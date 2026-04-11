"""
Trauma Vault CRUD endpoints.
Manages spatial pins on the 3D human model for injuries, surgeries, and stressors.
Protected with JWT authentication.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.core.security import get_current_user
from app.models.trauma import TraumaPin, TraumaCreate, TraumaUpdate, TraumaResponse
from app.models.user import User

router = APIRouter()


@router.get("/{patient_id}", response_model=List[TraumaResponse])
def get_trauma_pins(patient_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    GET /api/trauma/{patient_id}
    Returns ALL trauma pins for a patient.
    """
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    pins = (
        db.query(TraumaPin)
        .filter(TraumaPin.patient_id == patient_id)
        .order_by(TraumaPin.created_at.desc())
        .all()
    )
    return pins


@router.post("/", response_model=TraumaResponse, status_code=201)
def create_trauma_pin(data: TraumaCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    POST /api/trauma/
    Add a new trauma pin to the 3D model.
    """
    patient = db.query(User).filter(User.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{data.patient_id}' not found")

    valid_types = ["condition", "injury", "surgery", "psychological", "chronic_pain"]
    if data.trauma_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"trauma_type must be one of: {valid_types}")

    valid_severities = ["low", "medium", "high", "critical"]
    if data.severity not in valid_severities:
        raise HTTPException(status_code=400, detail=f"severity must be one of: {valid_severities}")

    pin = TraumaPin(**data.model_dump())
    db.add(pin)
    db.commit()
    db.refresh(pin)
    return pin


@router.put("/{pin_id}", response_model=TraumaResponse)
def update_trauma_pin(pin_id: str, data: TraumaUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    PUT /api/trauma/{pin_id}
    Update a trauma pin. Only send the fields you want to change.
    """
    pin = db.query(TraumaPin).filter(TraumaPin.id == pin_id).first()
    if not pin:
        raise HTTPException(status_code=404, detail=f"Trauma pin '{pin_id}' not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pin, key, value)

    db.commit()
    db.refresh(pin)
    return pin


@router.delete("/{pin_id}", status_code=204)
def delete_trauma_pin(pin_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    DELETE /api/trauma/{pin_id}
    Delete a trauma pin.
    """
    pin = db.query(TraumaPin).filter(TraumaPin.id == pin_id).first()
    if not pin:
        raise HTTPException(status_code=404, detail=f"Trauma pin '{pin_id}' not found")

    db.delete(pin)
    db.commit()
    return None
