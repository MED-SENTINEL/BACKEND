"""
AI Analysis model — stores results from all AI agents.
Each record = one agent execution (OCR, anomaly check, insight, chat).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from pydantic import BaseModel

from app.database import Base


class AIAnalysis(Base):
    """Stores AI-generated analysis results."""
    __tablename__ = "ai_analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(String, ForeignKey("lab_reports.id", ondelete="SET NULL"), nullable=True)
    analysis_type = Column(String, nullable=False)  # "ocr_extraction", "anomaly", "insight", "chat"
    result_json = Column(Text, nullable=False)       # Full JSON payload as string
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Pydantic Schemas ───

class AIAnalysisResponse(BaseModel):
    """Schema for API responses."""
    id: str
    patient_id: str
    report_id: Optional[str] = None
    analysis_type: str
    result_json: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Schema for LISA chat requests."""
    message: str


class ChatResponse(BaseModel):
    """Schema for LISA chat responses."""
    reply: str
    context_used: int  # How many records were used for context
