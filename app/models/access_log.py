"""
Access Log model and schemas.
Tracks when doctors access patient data via share keys.
Displayed to patients on their Access Control page for audit transparency.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, ForeignKey
from pydantic import BaseModel

from app.database import Base


class AccessLog(Base):
    """The 'access_logs' table. Records each time a share key is used."""
    __tablename__ = "access_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    share_key_id = Column(String, ForeignKey("share_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_name = Column(String, nullable=True)   # From the share key record or the doctor's profile
    doctor_id = Column(String, nullable=True)      # If the doctor is a registered user
    accessed_at = Column(DateTime, default=datetime.utcnow)
    action = Column(String, nullable=False, default="view")  # view, download, note_created


# ─── Pydantic Schemas ───

class AccessLogResponse(BaseModel):
    """Schema for returning access log entries to the patient."""
    id: str
    share_key_id: str
    patient_id: str
    doctor_name: Optional[str] = None
    doctor_id: Optional[str] = None
    accessed_at: datetime
    action: str

    class Config:
        from_attributes = True
