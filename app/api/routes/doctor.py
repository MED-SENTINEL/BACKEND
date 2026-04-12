"""
Doctor-specific API routes.
Notes CRUD + Clinical LISA + Access logs.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.doctor_note import DoctorNote, DoctorNoteCreate, DoctorNoteResponse
from app.models.access_log import AccessLog, AccessLogResponse

router = APIRouter()


# ─── Doctor Notes CRUD ───

@router.post("/notes", response_model=DoctorNoteResponse, status_code=201)
def create_note(
    data: DoctorNoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a clinical note for a patient."""
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can create clinical notes")

    valid_categories = ["observation", "diagnosis", "follow_up", "prescription"]
    if data.category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Category must be one of: {valid_categories}")

    note = DoctorNote(
        doctor_id=current_user.id,
        patient_id=data.patient_id,
        share_key_id=data.share_key_id,
        note_text=data.note_text,
        category=data.category,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/notes/{patient_id}", response_model=List[DoctorNoteResponse])
def get_notes(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all notes a doctor has written for a specific patient."""
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can view clinical notes")

    notes = (
        db.query(DoctorNote)
        .filter(DoctorNote.doctor_id == current_user.id, DoctorNote.patient_id == patient_id)
        .order_by(DoctorNote.created_at.desc())
        .all()
    )
    return notes


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a doctor note. Only the author can delete."""
    note = db.query(DoctorNote).filter(DoctorNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own notes")

    db.delete(note)
    db.commit()
    return None


# ─── Clinical LISA ───

@router.post("/lisa-clinical")
def clinical_lisa_chat(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Chat with LISA using a clinical system prompt.
    Expects: { message: str, patient_id: str }
    """
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can use Clinical LISA")

    from app.services.lisa_service import chat as lisa_chat

    message = body.get("message", "")
    patient_id = body.get("patient_id", "")

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    # Build patient context
    from app.api.routes.ai import _build_patient_data
    patient_data = _build_patient_data(db, patient_id) if patient_id else {}

    # Override with clinical system prompt
    clinical_context = {
        **patient_data,
        "system_mode": "clinical",
    }

    reply = lisa_chat(message, clinical_context)

    return {
        "reply": reply,
        "context_used": len(patient_data.get("extractions", [])) + len(patient_data.get("trauma_pins", [])),
    }


# ─── Access Logs ───

@router.get("/access-logs/{patient_id}", response_model=List[AccessLogResponse])
def get_access_logs(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get access logs for a patient. 
    Patients can see who accessed their data. Doctors can see their own access history.
    """
    if current_user.role == "patient" and current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="You can only view your own access logs")

    query = db.query(AccessLog).filter(AccessLog.patient_id == patient_id)

    if current_user.role == "doctor":
        # Doctors only see their own access logs for this patient
        query = query.filter(AccessLog.doctor_id == current_user.id)

    logs = query.order_by(AccessLog.accessed_at.desc()).limit(100).all()
    return logs
