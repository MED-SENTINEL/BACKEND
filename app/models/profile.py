"""
Patient Profile model and schemas.
Stores medical/personal data collected during onboarding.
Separate from auth to keep user table lean.
"""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, String, Float, Integer, Date, DateTime, ForeignKey
from pydantic import BaseModel

from app.database import Base


class PatientProfile(Base):
    """The 'patient_profiles' table. One-to-one with users."""
    __tablename__ = "patient_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Demographics
    gender = Column(String, nullable=True)              # "male", "female", "other", "prefer_not_to_say"
    date_of_birth = Column(Date, nullable=True)
    blood_type = Column(String, nullable=True)          # "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"

    # Physical
    height_cm = Column(Float, nullable=True)            # Height in centimeters
    weight_kg = Column(Float, nullable=True)            # Weight in kilograms

    # Contact
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)

    # Emergency
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    emergency_contact_relation = Column(String, nullable=True)  # "parent", "spouse", "sibling", etc.

    # Medical
    allergies = Column(String, nullable=True)           # Comma-separated or free text
    chronic_conditions = Column(String, nullable=True)  # e.g., "Diabetes Type 2, Hypertension"
    current_medications = Column(String, nullable=True) # Free text
    past_surgeries = Column(String, nullable=True)      # Free text

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Pydantic Schemas ───

class ProfileCreate(BaseModel):
    """Schema for onboarding — creating a patient profile."""
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    blood_type: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    past_surgeries: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Schema for updating profile. All fields optional."""
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    blood_type: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    past_surgeries: Optional[str] = None


class ProfileResponse(BaseModel):
    """Schema for returning profile data."""
    id: str
    user_id: str
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    blood_type: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    past_surgeries: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
