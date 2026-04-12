"""
Doctor Profile model and schemas.
Stores professional data collected during doctor onboarding.
Separate from auth to keep user table lean.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from pydantic import BaseModel

from app.database import Base


class DoctorProfile(Base):
    """The 'doctor_profiles' table. One-to-one with users where role='doctor'."""
    __tablename__ = "doctor_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Professional
    specialty = Column(String, nullable=True)          # e.g. "Cardiology", "General Medicine"
    license_number = Column(String, nullable=True)     # Medical license / registration number
    hospital = Column(String, nullable=True)           # Primary hospital affiliation
    department = Column(String, nullable=True)         # Department within hospital
    years_of_experience = Column(Integer, nullable=True)

    # Contact
    phone = Column(String, nullable=True)
    bio = Column(String, nullable=True)                # Short professional bio

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Pydantic Schemas ───

class DoctorProfileCreate(BaseModel):
    """Schema for doctor onboarding."""
    specialty: Optional[str] = None
    license_number: Optional[str] = None
    hospital: Optional[str] = None
    department: Optional[str] = None
    years_of_experience: Optional[int] = None
    phone: Optional[str] = None
    bio: Optional[str] = None


class DoctorProfileUpdate(BaseModel):
    """Schema for updating doctor profile."""
    specialty: Optional[str] = None
    license_number: Optional[str] = None
    hospital: Optional[str] = None
    department: Optional[str] = None
    years_of_experience: Optional[int] = None
    phone: Optional[str] = None
    bio: Optional[str] = None


class DoctorProfileResponse(BaseModel):
    """Schema for returning doctor profile data."""
    id: str
    user_id: str
    specialty: Optional[str] = None
    license_number: Optional[str] = None
    hospital: Optional[str] = None
    department: Optional[str] = None
    years_of_experience: Optional[int] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
