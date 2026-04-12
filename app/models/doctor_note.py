"""
Doctor Note model and schemas.
Clinical notes written by doctors during patient review sessions.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from pydantic import BaseModel

from app.database import Base


class DoctorNote(Base):
    """The 'doctor_notes' table. Notes written by doctors about patients."""
    __tablename__ = "doctor_notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    share_key_id = Column(String, ForeignKey("share_keys.id", ondelete="SET NULL"), nullable=True)

    note_text = Column(Text, nullable=False)
    category = Column(String, nullable=False, default="observation")  # observation, diagnosis, follow_up, prescription

    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Pydantic Schemas ───

class DoctorNoteCreate(BaseModel):
    """Schema for creating a doctor note."""
    patient_id: str
    share_key_id: Optional[str] = None
    note_text: str
    category: str = "observation"  # observation, diagnosis, follow_up, prescription


class DoctorNoteResponse(BaseModel):
    """Schema for returning a doctor note."""
    id: str
    doctor_id: str
    patient_id: str
    share_key_id: Optional[str] = None
    note_text: str
    category: str
    created_at: datetime

    class Config:
        from_attributes = True
