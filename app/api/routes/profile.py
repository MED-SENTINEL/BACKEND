"""
Patient & Doctor Profile endpoints.
Onboarding and profile management — collect data after registration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.profile import PatientProfile, ProfileCreate, ProfileUpdate, ProfileResponse
from app.models.doctor_profile import DoctorProfile, DoctorProfileCreate, DoctorProfileResponse

router = APIRouter()


@router.post("/onboard", status_code=201)
def onboard(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    POST /api/profile/onboard
    Create the profile during onboarding.
    Accepts an optional 'role' field to set the user's role (patient/doctor).
    """
    # Allow role to be set during onboarding
    chosen_role = data.pop("role", None)
    if chosen_role in ("patient", "doctor"):
        current_user.role = chosen_role

    if current_user.role == "doctor":
        # Doctor onboarding
        existing = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Doctor profile already exists. Use PUT to update.")

        doc_data = DoctorProfileCreate(**data)
        profile = DoctorProfile(
            user_id=current_user.id,
            **doc_data.model_dump(exclude_unset=True),
        )
        db.add(profile)
        current_user.is_onboarded = True
        db.commit()
        db.refresh(profile)
        return profile
    else:
        # Patient onboarding (existing behavior)
        existing = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Profile already exists. Use PUT to update.")

        patient_data = ProfileCreate(**data)
        profile = PatientProfile(
            user_id=current_user.id,
            **patient_data.model_dump(exclude_unset=True),
        )
        db.add(profile)
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
