"""
Patient Profile endpoints.
Onboarding and profile management — collect medical data after registration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.profile import PatientProfile, ProfileCreate, ProfileUpdate, ProfileResponse

router = APIRouter()


@router.post("/onboard", response_model=ProfileResponse, status_code=201)
def onboard(data: ProfileCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    POST /api/profile/onboard
    Create the patient profile during onboarding.
    Can only be called once per user. Marks user as onboarded.
    """
    # Check if profile already exists
    existing = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Profile already exists. Use PUT to update.")

    # Create profile
    profile = PatientProfile(
        user_id=current_user.id,
        **data.model_dump(exclude_unset=True),
    )
    db.add(profile)

    # Mark user as onboarded
    current_user.is_onboarded = True
    db.commit()
    db.refresh(profile)

    return profile


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    GET /api/profile/me
    Returns the current user's patient profile.
    """
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Complete onboarding first.")
    return profile


@router.put("/me", response_model=ProfileResponse)
def update_my_profile(data: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    PUT /api/profile/me
    Update the current user's patient profile. Only send fields you want to change.
    """
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Complete onboarding first.")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{patient_id}", response_model=ProfileResponse)
def get_patient_profile(patient_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    GET /api/profile/{patient_id}
    Returns a patient's profile by user ID. Useful for doctor-side views.
    """
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == patient_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found for this patient.")
    return profile
