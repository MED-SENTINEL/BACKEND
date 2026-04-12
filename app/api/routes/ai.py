"""
AI Agents Router — Orchestrates all AI-powered features.

Endpoints:
  POST /analyze/{report_id}    — Run OCR extraction + anomaly detection on a lab report
  POST /insights/{patient_id}  — Generate comprehensive health insights
  POST /chat                   — Chat with LISA, the patient's AI assistant
  GET  /history/{patient_id}   — Retrieve past AI analysis records
"""

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.core.security import get_current_user
from app.models.user import User
from app.models.report import LabReport
from app.models.ai_analysis import AIAnalysis, ChatRequest, ChatResponse

from app.services.ocr_service import extract_report_data
from app.services.anomaly_service import run_anomaly_check
from app.services.insight_service import generate_health_insights
from app.services.lisa_service import chat as lisa_chat

router = APIRouter()


# ─── Dependency ───

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── POST /analyze/{report_id} ───────────────────────────────────────────────

@router.post("/analyze/{report_id}")
def analyze_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run AI analysis on a specific lab report:
    1. OCR extraction (via Gemini vision)
    2. Anomaly detection (threshold + AI trend analysis)
    
    Stores results in ai_analyses table and updates the report's extracted_data.
    """
    # Fetch the report
    report = db.query(LabReport).filter(
        LabReport.id == report_id,
        LabReport.patient_id == current_user.id,
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Step 1: OCR Extraction
    extraction = extract_report_data(report.file_path, report.file_type)

    # Save extraction to the report
    report.extracted_data = json.dumps(extraction, default=str)
    db.commit()

    # Store OCR result in AI analyses
    ocr_record = AIAnalysis(
        patient_id=current_user.id,
        report_id=report_id,
        analysis_type="ocr_extraction",
        result_json=json.dumps(extraction, default=str),
    )
    db.add(ocr_record)

    # Step 2: Anomaly Detection
    # Get historical extractions for trend analysis
    historical = _get_patient_extractions(db, current_user.id)
    alerts = run_anomaly_check(extraction, historical)

    anomaly_result = {"alerts": alerts, "total_alerts": len(alerts)}

    if alerts:
        anomaly_record = AIAnalysis(
            patient_id=current_user.id,
            report_id=report_id,
            analysis_type="anomaly",
            result_json=json.dumps(anomaly_result, default=str),
        )
        db.add(anomaly_record)

    db.commit()

    return {
        "extraction": extraction,
        "alerts": alerts,
        "report_id": report_id,
        "status": "analysis_complete",
    }


# ─── POST /insights/{patient_id} ─────────────────────────────────────────────

@router.post("/insights/{patient_id}")
def get_insights(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate comprehensive health insights from all of a patient's data.
    Clears old insights/anomaly records and regenerates from current bloodwork.
    """
    if current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # ─── Clear ALL stale insight and anomaly records ───
    db.query(AIAnalysis).filter(
        AIAnalysis.patient_id == patient_id,
        AIAnalysis.analysis_type.in_(["insight", "anomaly", "ocr_extraction"]),
    ).delete(synchronize_session=False)
    db.commit()

    # ─── Build patient data (pulls from bloodwork_entries + trauma_pins) ───
    patient_data = _build_patient_data(db, patient_id)
    extractions = patient_data.get("extractions", [])

    # ─── Run anomaly checks LIVE on each extraction ───
    all_alerts = []
    for ext in extractions:
        try:
            alerts = run_anomaly_check(ext)
            all_alerts.extend(alerts)
        except Exception as e:
            print(f"[AI] Anomaly check failed: {e}")

    # Store fresh anomaly records
    if all_alerts:
        anomaly_record = AIAnalysis(
            patient_id=patient_id,
            analysis_type="anomaly",
            result_json=json.dumps({"alerts": all_alerts}, default=str),
        )
        db.add(anomaly_record)

    # ─── Generate insights from current data ───
    insights = generate_health_insights(patient_data)

    # Store fresh insight record
    insight_record = AIAnalysis(
        patient_id=patient_id,
        analysis_type="insight",
        result_json=json.dumps(insights, default=str),
    )
    db.add(insight_record)
    db.commit()

    return {
        "insights": insights,
        "alerts": all_alerts,
        "reports_analyzed": len(extractions),
    }


# ─── POST /chat ──────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat_with_lisa(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Chat with LISA, the AI health assistant.
    Loads all patient data into context for personalized responses.
    """
    patient_data = _build_patient_data(db, current_user.id)
    reply = lisa_chat(body.message, patient_data)

    # Store the chat interaction
    chat_record = AIAnalysis(
        patient_id=current_user.id,
        analysis_type="chat",
        result_json=json.dumps({
            "question": body.message,
            "reply": reply,
        }, default=str),
    )
    db.add(chat_record)
    db.commit()

    return ChatResponse(
        reply=reply,
        context_used=len(patient_data.get("extractions", [])) + len(patient_data.get("trauma_pins", [])),
    )


# ─── GET /history/{patient_id} ───────────────────────────────────────────────

@router.get("/history/{patient_id}")
def get_analysis_history(
    patient_id: str,
    analysis_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve past AI analysis records for a patient.
    Optionally filter by analysis_type (ocr_extraction, anomaly, insight, chat).
    """
    if current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(AIAnalysis).filter(AIAnalysis.patient_id == patient_id)

    if analysis_type:
        query = query.filter(AIAnalysis.analysis_type == analysis_type)

    records = query.order_by(AIAnalysis.created_at.desc()).limit(50).all()

    return [
        {
            "id": r.id,
            "analysis_type": r.analysis_type,
            "report_id": r.report_id,
            "result": json.loads(r.result_json) if r.result_json else {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_patient_extractions(db: Session, patient_id: str) -> list:
    """Get all parsed lab extractions for a patient (for trend analysis)."""
    reports = db.query(LabReport).filter(
        LabReport.patient_id == patient_id,
        LabReport.extracted_data.isnot(None),
    ).order_by(LabReport.uploaded_at.asc()).all()

    extractions = []
    for r in reports:
        try:
            extractions.append(json.loads(r.extracted_data))
        except (json.JSONDecodeError, TypeError):
            continue
    return extractions


def _build_patient_data(db: Session, patient_id: str) -> dict:
    """Build the full patient data context for AI services."""
    from app.models.trauma import TraumaPin
    from app.models.profile import PatientProfile
    from app.models.bloodwork import BloodworkEntry

    # ─── Primary: Bloodwork entries (manually entered) ───
    bloodwork_records = db.query(BloodworkEntry).filter(
        BloodworkEntry.patient_id == patient_id,
    ).order_by(BloodworkEntry.test_date.asc()).all()

    extractions = []
    for bw in bloodwork_records:
        try:
            values = json.loads(bw.values_json) if bw.values_json else {}
            extractions.append({
                "report_type": bw.label or "Manual Entry",
                "report_date": str(bw.test_date) if bw.test_date else None,
                "values": values,
                "flags": [],
                "extraction_mode": "manual",
            })
        except (json.JSONDecodeError, TypeError):
            continue

    # ─── Secondary: OCR extractions from lab reports (REMOVED) ───
    # We no longer read from LabReport.extracted_data to ensure insights
    # only use verified manual bloodwork entries and eliminate stale data.

    # Trauma pins
    trauma_records = db.query(TraumaPin).filter(
        TraumaPin.patient_id == patient_id
    ).all()
    trauma_pins = [
        {
            "trauma_type": t.trauma_type,
            "severity": t.severity,
            "body_region": t.body_region,
            "description": t.notes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in trauma_records
    ]

    # Profile
    from app.models.user import User
    from datetime import date

    user = db.query(User).filter(User.id == patient_id).first()
    profile = db.query(PatientProfile).filter(
        PatientProfile.user_id == patient_id
    ).first()

    profile_data = None
    if user:
        profile_data = {
            "full_name": user.full_name,
            "gender": profile.gender if profile else "Unknown",
            "blood_type": profile.blood_type if profile else "Unknown",
            "age": "Unknown"
        }
        
        if profile and profile.date_of_birth:
            today = date.today()
            dob = profile.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            profile_data["age"] = age

    # Previous insights (most recent)
    last_insight = db.query(AIAnalysis).filter(
        AIAnalysis.patient_id == patient_id,
        AIAnalysis.analysis_type == "insight",
    ).order_by(AIAnalysis.created_at.desc()).first()

    insights = None
    if last_insight:
        try:
            insights = json.loads(last_insight.result_json)
        except (json.JSONDecodeError, TypeError):
            pass

    # Recent anomaly alerts
    last_anomaly = db.query(AIAnalysis).filter(
        AIAnalysis.patient_id == patient_id,
        AIAnalysis.analysis_type == "anomaly",
    ).order_by(AIAnalysis.created_at.desc()).first()

    alerts = []
    if last_anomaly:
        try:
            anomaly_data = json.loads(last_anomaly.result_json)
            alerts = anomaly_data.get("alerts", [])
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "profile": profile_data,
        "extractions": extractions,
        "trauma_pins": trauma_pins,
        "insights": insights,
        "alerts": alerts,
    }

