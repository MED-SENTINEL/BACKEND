"""
Trauma Pin model and schemas.
Stores spatial coordinates of injuries/surgeries pinned on the 3D human model.
"""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, String, Float, Date, DateTime, ForeignKey
from pydantic import BaseModel

from app.database import Base


class TraumaPin(Base):
    """The 'trauma_pins' table. Each row = one pin on the 3D model."""
    __tablename__ = "trauma_pins"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 3D coordinates on the human model (from Three.js raycasting)
    position_x = Column(Float, nullable=False)
    position_y = Column(Float, nullable=False)
    position_z = Column(Float, nullable=False)

    # Trauma details
    trauma_type = Column(String, nullable=False)  # "injury", "surgery", "psychological", "chronic_pain"
    title = Column(String, nullable=False)         # Short label, e.g., "Left knee ACL tear"
    notes = Column(String, nullable=True)          # Detailed notes (plain text in dev, encrypted in prod)
    severity = Column(String, nullable=False, default="medium")  # "low", "medium", "high", "critical"
    body_region = Column(String, nullable=True)    # "head", "torso", "left_arm", "right_leg", etc.

    # Links
    linked_report_id = Column(String, ForeignKey("lab_reports.id"), nullable=True)
    occurred_at = Column(Date, nullable=True)      # When the trauma occurred

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Pydantic Schemas ───

class TraumaCreate(BaseModel):
    """Schema for creating a new trauma pin."""
    patient_id: str
    position_x: float
    position_y: float
    position_z: float
    trauma_type: str            # "injury", "surgery", "psychological", "chronic_pain"
    title: str                  # Short label
    notes: Optional[str] = None
    severity: str = "medium"    # "low", "medium", "high", "critical"
    body_region: Optional[str] = None
    linked_report_id: Optional[str] = None
    occurred_at: Optional[date] = None


class TraumaUpdate(BaseModel):
    """Schema for updating a trauma pin. All fields optional."""
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    position_z: Optional[float] = None
    trauma_type: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    severity: Optional[str] = None
    body_region: Optional[str] = None
    linked_report_id: Optional[str] = None
    occurred_at: Optional[date] = None


class TraumaResponse(BaseModel):
    """Schema for returning trauma data in API responses."""
    id: str
    patient_id: str
    position_x: float
    position_y: float
    position_z: float
    trauma_type: str
    title: str
    notes: Optional[str] = None
    severity: str
    body_region: Optional[str] = None
    linked_report_id: Optional[str] = None
    occurred_at: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
