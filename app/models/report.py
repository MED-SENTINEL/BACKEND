"""
Lab Report model and schemas.
Simplified to file-upload-only. No OCR extraction or manual data entry.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from pydantic import BaseModel

from app.database import Base


class LabReport(Base):
    """The 'lab_reports' table. Each row = one uploaded file."""
    __tablename__ = "lab_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String, nullable=False)       # Original filename
    file_path = Column(String, nullable=False)       # Path on disk
    file_type = Column(String, nullable=False)       # "pdf", "jpg", "png"
    label = Column(String, nullable=True)            # Optional user-provided label
    extracted_data = Column(Text, nullable=True)     # JSON: AI-extracted lab values
    uploaded_at = Column(DateTime, default=datetime.utcnow)


# ─── Pydantic Schemas ───

class ReportResponse(BaseModel):
    """Schema for returning report data in API responses."""
    id: str
    patient_id: str
    file_name: str
    file_type: str
    label: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True
