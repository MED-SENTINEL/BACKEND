"""
User model and schemas for SENTINEL.
Slim auth-focused model. Profile data is in a separate model.
"""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime
from pydantic import BaseModel, EmailStr

from app.database import Base


# ─── SQLAlchemy ORM Model ───

class User(Base):
    """The 'users' table. Auth-focused: email, password, verification."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    google_id = Column(String, unique=True, nullable=True)

    # Verification
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String, nullable=True)
    verification_expires_at = Column(DateTime, nullable=True)

    # Onboarding
    is_onboarded = Column(Boolean, default=False, nullable=False)
    role = Column(String, nullable=False, default="patient")  # "patient" or "doctor"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Pydantic Schemas ───

class RegisterRequest(BaseModel):
    """Schema for user registration."""
    email: str
    role: Optional[str] = "patient"  # "patient" or "doctor"
    password: str
    full_name: str


class LoginRequest(BaseModel):
    """Schema for user login."""
    email: str
    password: str


class VerifyRequest(BaseModel):
    """Schema for email verification."""
    email: str
    code: str


class ResendCodeRequest(BaseModel):
    """Schema for resending verification code."""
    email: str


class UserResponse(BaseModel):
    """Schema for returning user data (never includes password)."""
    id: str
    email: str
    full_name: str
    is_verified: bool
    is_onboarded: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MeResponse(BaseModel):
    """Extended user response that includes profile fields.
    Used by /api/auth/me so the frontend gets everything in one call."""
    # Auth fields
    id: str
    email: str
    full_name: str
    role: str = "patient"
    is_verified: bool
    is_onboarded: bool
    created_at: datetime
    updated_at: datetime

    # Profile fields (optional — null if not onboarded yet)
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

    # Doctor profile fields (only populated if role == "doctor")
    specialty: Optional[str] = None
    license_number: Optional[str] = None
    hospital: Optional[str] = None
    department: Optional[str] = None
    years_of_experience: Optional[int] = None
    bio: Optional[str] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Schema for login response with JWT token."""
    user: UserResponse
    token: str


class UserUpdate(BaseModel):
    """Schema for updating user auth fields."""
    full_name: Optional[str] = None
