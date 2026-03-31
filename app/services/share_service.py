"""
Share-Key generation and validation logic.
Uses profile model for patient data in doctor access response.
"""

import uuid
import hashlib
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.share_key import ShareKey
from app.models.user import User
from app.models.profile import PatientProfile
from app.models.report import LabReport
from app.models.trauma import TraumaPin


def hash_passcode(passcode: str) -> str:
    """Hash a passcode using SHA-256."""
    return hashlib.sha256(passcode.encode()).hexdigest()


def generate_share_key(
    db: Session,
    patient_id: str,
    passcode: str,
    permissions: str = "full",
    expires_in_hours: int = 24,
    max_uses: int = 5,
    doctor_name: str = None,
    doctor_specialty: str = None,
    label: str = None,
) -> ShareKey:
    """Generate a new share-key for a patient."""
    key = str(uuid.uuid4())
    passcode_hashed = hash_passcode(passcode)
    expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

    share_key = ShareKey(
        patient_id=patient_id,
        share_key=key,
        passcode_hash=passcode_hashed,
        permissions=permissions,
        expires_at=expires_at,
        max_uses=max_uses,
        doctor_name=doctor_name,
        doctor_specialty=doctor_specialty,
        label=label,
    )

    db.add(share_key)
    db.commit()
    db.refresh(share_key)

    return share_key


def validate_share_key(db: Session, key: str, passcode: str, increment_usage: bool = True) -> dict:
    """
    Validate a share-key and passcode. If valid, return the patient's data.
    Raises ValueError on failure.
    """
    share_key = db.query(ShareKey).filter(ShareKey.share_key == key).first()
    if not share_key:
        raise ValueError("Share-key not found.")

    if share_key.is_revoked:
        raise ValueError("This share-key has been revoked by the patient.")

    if datetime.utcnow() > share_key.expires_at:
        raise ValueError("This share-key has expired.")

    if share_key.usage_count >= share_key.max_uses:
        raise ValueError(f"This share-key has reached its maximum uses ({share_key.max_uses}).")

    if hash_passcode(passcode) != share_key.passcode_hash:
        raise ValueError("Invalid passcode.")

    # All checks passed — increment usage count only if requested
    if increment_usage:
        share_key.usage_count += 1
        db.commit()

    # Fetch patient data
    patient_id = share_key.patient_id

    # Get patient user + profile
    patient = db.query(User).filter(User.id == patient_id).first()
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == patient_id).first()

    patient_profile = {
        "id": patient.id,
        "full_name": patient.full_name,
        "email": patient.email,
        "gender": profile.gender if profile else None,
        "date_of_birth": str(profile.date_of_birth) if profile and profile.date_of_birth else None,
        "blood_type": profile.blood_type if profile else None,
        "height_cm": profile.height_cm if profile else None,
        "weight_kg": profile.weight_kg if profile else None,
        "allergies": profile.allergies if profile else None,
        "chronic_conditions": profile.chronic_conditions if profile else None,
        "current_medications": profile.current_medications if profile else None,
    }

    # Fetch data based on permission scope
    lab_reports = []
    trauma_pins = []

    if share_key.permissions in ("full", "labs_only"):
        report_records = (
            db.query(LabReport)
            .filter(LabReport.patient_id == patient_id)
            .order_by(LabReport.uploaded_at.desc())
            .all()
        )
        lab_reports = [
            {
                "id": r.id,
                "file_name": r.file_name,
                "file_type": r.file_type,
                "label": r.label,
                "uploaded_at": str(r.uploaded_at),
            }
            for r in report_records
        ]

    if share_key.permissions == "full":
        pin_records = (
            db.query(TraumaPin)
            .filter(TraumaPin.patient_id == patient_id)
            .order_by(TraumaPin.created_at.desc())
            .all()
        )
        trauma_pins = [
            {
                "id": p.id,
                "position_x": p.position_x,
                "position_y": p.position_y,
                "position_z": p.position_z,
                "trauma_type": p.trauma_type,
                "title": p.title,
                "notes": p.notes,
                "severity": p.severity,
                "body_region": p.body_region,
                "occurred_at": str(p.occurred_at) if p.occurred_at else None,
            }
            for p in pin_records
        ]

    return {
        "patient_profile": patient_profile,
        "lab_reports": lab_reports,
        "trauma_pins": trauma_pins,
        "permissions": share_key.permissions,
        "key_expires_at": share_key.expires_at,
        "usage_remaining": share_key.max_uses - share_key.usage_count,
    }
