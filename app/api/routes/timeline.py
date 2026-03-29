"""
Timeline endpoint.
Returns chronological patient data for the time-travel slider UI.
Protected with JWT authentication.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.report import LabReport
from app.models.trauma import TraumaPin

router = APIRouter()


@router.get("/{patient_id}")
def get_timeline(patient_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    GET /api/timeline/{patient_id}
    Returns ALL patient data merged into a chronological timeline.
    """
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    timeline = []

    # Removed biometrics

    # Add lab reports (simplified — file info only)
    reports = db.query(LabReport).filter(LabReport.patient_id == patient_id).all()
    for r in reports:
        timeline.append({
            "type": "report",
            "timestamp": r.uploaded_at.isoformat(),
            "data": {
                "id": r.id,
                "file_name": r.file_name,
                "file_type": r.file_type,
                "label": r.label,
            },
        })

    # Add trauma pins
    pins = db.query(TraumaPin).filter(TraumaPin.patient_id == patient_id).all()
    for p in pins:
        timestamp = p.occurred_at.isoformat() if p.occurred_at else p.created_at.isoformat()
        timeline.append({
            "type": "trauma",
            "timestamp": timestamp,
            "data": {
                "id": p.id,
                "title": p.title,
                "trauma_type": p.trauma_type,
                "severity": p.severity,
                "body_region": p.body_region,
                "position": {"x": p.position_x, "y": p.position_y, "z": p.position_z},
                "notes": p.notes,
            },
        })

    # Removed predictions

    # Sort by timestamp (newest first - descending)
    timeline.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "patient_id": patient_id,
        "patient_name": patient.full_name,
        "total_events": len(timeline),
        "timeline": timeline,
    }
