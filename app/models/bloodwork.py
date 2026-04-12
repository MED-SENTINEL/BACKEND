"""
Bloodwork model — Manually entered lab values.

Each entry represents a set of blood test results from a specific date.
Values are stored as a JSON blob for flexibility.
"""

import uuid
from datetime import datetime, date as date_type
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.database import Base


class BloodworkEntry(Base):
    __tablename__ = "bloodwork_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("users.id"), nullable=False)
    test_date = Column(Date, nullable=False)
    label = Column(String, nullable=True)  # e.g., "Annual Checkup", "Liver Function"
    values_json = Column(Text, nullable=False)  # JSON: {test_name: {value, unit, reference_range, status}}
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Pydantic Schemas ───

class BloodworkValueItem(BaseModel):
    value: float
    unit: str
    reference_range: str = ""
    status: str = "normal"  # normal, elevated, low, critical


class BloodworkCreate(BaseModel):
    test_date: str  # YYYY-MM-DD
    label: Optional[str] = None
    values: Dict[str, BloodworkValueItem]


class BloodworkResponse(BaseModel):
    id: str
    patient_id: str
    test_date: str
    label: Optional[str] = None
    values: Dict[str, Any]
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
