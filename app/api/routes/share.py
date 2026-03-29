"""
Share-Key endpoints.
Protected with JWT authentication.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.core.security import get_current_user
from app.models.share_key import ShareKey, ShareKeyCreate, ShareKeyValidate, ShareKeyResponse, DoctorAccessResponse
from app.models.user import User
from app.services.share_service import generate_share_key, validate_share_key

router = APIRouter()


@router.post("/generate", response_model=ShareKeyResponse, status_code=201)
def create_share_key(data: ShareKeyCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    POST /api/share/generate
    Patient generates a new share-key.
    """
    patient = db.query(User).filter(User.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{data.patient_id}' not found")

    if not data.passcode.isdigit() or len(data.passcode) < 4 or len(data.passcode) > 6:
        raise HTTPException(status_code=400, detail="Passcode must be 4-6 digits")

    valid_perms = ["full", "labs_only"]
    if data.permissions not in valid_perms:
        raise HTTPException(status_code=400, detail=f"permissions must be one of: {valid_perms}")

    key = generate_share_key(
        db=db,
        patient_id=data.patient_id,
        passcode=data.passcode,
        permissions=data.permissions,
        expires_in_hours=data.expires_in_hours,
        max_uses=data.max_uses,
        doctor_name=data.doctor_name,
        doctor_specialty=data.doctor_specialty,
        label=data.label,
    )

    return key


@router.post("/validate/{share_key}", response_model=DoctorAccessResponse)
def validate_key(share_key: str, data: ShareKeyValidate, db: Session = Depends(get_db)):
    """
    POST /api/share/validate/{share_key}
    Doctor validates a share-key. This endpoint is PUBLIC (no JWT needed).
    """
    try:
        result = validate_share_key(db, share_key, data.passcode)
        return result
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/list/{patient_id}", response_model=List[ShareKeyResponse])
def list_share_keys(patient_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    GET /api/share/list/{patient_id}
    Patient lists all their share-keys.
    """
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    keys = (
        db.query(ShareKey)
        .filter(ShareKey.patient_id == patient_id)
        .order_by(ShareKey.created_at.desc())
        .all()
    )
    return keys


@router.post("/revoke/{key_id}")
def revoke_share_key(key_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    POST /api/share/revoke/{key_id}
    Patient revokes a share-key.
    """
    key = db.query(ShareKey).filter(ShareKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail=f"Share-key '{key_id}' not found")

    if key.is_revoked:
        raise HTTPException(status_code=400, detail="This key is already revoked")

    key.is_revoked = True
    db.commit()

    return {"message": f"Share-key '{key_id}' has been revoked", "is_revoked": True}
