"""
Bloodwork endpoints — Manual lab value entry.
Protected with JWT authentication.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import SessionLocal
from app.core.security import get_current_user
from app.models.user import User
from app.models.bloodwork import BloodworkEntry, BloodworkCreate, BloodworkResponse

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{patient_id}", response_model=List[BloodworkResponse])
def get_bloodwork(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all bloodwork entries for a patient, newest first."""
    if current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="Access denied")

    entries = (
        db.query(BloodworkEntry)
        .filter(BloodworkEntry.patient_id == patient_id)
        .order_by(BloodworkEntry.test_date.desc())
        .all()
    )

    return [
        BloodworkResponse(
            id=e.id,
            patient_id=e.patient_id,
            test_date=str(e.test_date),
            label=e.label,
            values=json.loads(e.values_json) if e.values_json else {},
            created_at=e.created_at.isoformat() if e.created_at else None,
        )
        for e in entries
    ]


@router.post("/", response_model=BloodworkResponse, status_code=201)
def create_bloodwork(
    body: BloodworkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new bloodwork entry with manually entered values."""
    from datetime import date as date_type

    # Parse test_date string to date object
    try:
        parsed_date = date_type.fromisoformat(body.test_date)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid date format: {body.test_date}. Use YYYY-MM-DD.")

    # Build values dict
    values_with_status = {}
    for test_name, item in body.values.items():
        values_with_status[test_name] = {
            "value": item.value,
            "unit": item.unit,
            "reference_range": item.reference_range,
            "status": item.status,
        }

    try:
        entry = BloodworkEntry(
            patient_id=current_user.id,
            test_date=parsed_date,
            label=body.label,
            values_json=json.dumps(values_with_status),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return BloodworkResponse(
        id=entry.id,
        patient_id=entry.patient_id,
        test_date=str(entry.test_date),
        label=entry.label,
        values=values_with_status,
        created_at=entry.created_at.isoformat() if entry.created_at else None,
    )


@router.delete("/{entry_id}", status_code=204)
def delete_bloodwork(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a bloodwork entry."""
    entry = db.query(BloodworkEntry).filter(BloodworkEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.delete(entry)
    db.commit()
    return None
