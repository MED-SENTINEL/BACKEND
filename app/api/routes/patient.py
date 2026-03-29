"""
Patient CRUD endpoints.
Protected with JWT authentication.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserUpdate, UserResponse

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
def list_patients(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    GET /api/patients/
    Returns a list of ALL patients in the database.
    """
    patients = db.query(User).all()
    return patients


@router.get("/{patient_id}", response_model=UserResponse)
def get_patient(patient_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    GET /api/patients/{patient_id}
    Returns a single patient by their ID.
    """
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
    return patient


@router.put("/{patient_id}", response_model=UserResponse)
def update_patient(patient_id: str, data: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    PUT /api/patients/{patient_id}
    Updates a patient's info. Only sends the fields you want to change.
    """
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(patient, key, value)

    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    DELETE /api/patients/{patient_id}
    Permanently deletes a patient and all their related data.
    """
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    db.delete(patient)
    db.commit()
    return None
