"""
Lab Report endpoints — file upload only.
Protected with JWT authentication.
"""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.report import LabReport, ReportResponse
from app.models.user import User

router = APIRouter()


@router.get("/{patient_id}", response_model=List[ReportResponse])
def get_reports(patient_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    GET /api/reports/{patient_id}
    Returns ALL lab reports for a patient, newest first.
    """
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    reports = (
        db.query(LabReport)
        .filter(LabReport.patient_id == patient_id)
        .order_by(LabReport.uploaded_at.desc())
        .all()
    )
    return reports


@router.post("/upload", response_model=ReportResponse, status_code=201)
async def upload_report(
    patient_id: str = Form(...),
    label: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    POST /api/reports/upload
    Upload a lab report file (image or PDF).

    Send as multipart/form-data with fields:
    - patient_id: string
    - file: the image/PDF file
    - label: optional description
    """
    # Verify patient exists
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    # Determine file type
    file_ext = file.filename.split(".")[-1].lower() if file.filename else "unknown"
    if file_ext not in ["pdf", "jpg", "jpeg", "png"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}. Use PDF, JPG, or PNG.")

    # Save the file to disk in a user-specific subfolder
    file_id = str(uuid.uuid4())
    save_name = f"{file_id}.{file_ext}"

    user_upload_dir = os.path.join(settings.UPLOAD_DIR, patient_id)
    os.makedirs(user_upload_dir, exist_ok=True)

    save_path = os.path.join(user_upload_dir, save_name)

    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Save report to database
    report = LabReport(
        patient_id=patient_id,
        file_name=file.filename,
        file_path=save_path,
        file_type=file_ext,
        label=label,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/file/{report_id}")
async def get_report_file(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    GET /api/reports/file/{report_id}
    Retrieves the raw report file. Ownership check via JWT.
    """
    report = db.query(LabReport).filter(LabReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Ownership check: only allow the owner to access their file
    if report.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Determine media type
    media_type = "application/pdf"
    if report.file_type in ["jpg", "jpeg"]:
        media_type = "image/jpeg"
    elif report.file_type == "png":
        media_type = "image/png"

    return FileResponse(
        path=report.file_path,
        media_type=media_type,
        filename=report.file_name,
    )


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    DELETE /api/reports/{report_id}
    Delete a lab report and its uploaded file.
    """
    report = db.query(LabReport).filter(LabReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")

    # Delete uploaded file
    if report.file_path and os.path.exists(report.file_path):
        os.remove(report.file_path)

    db.delete(report)
    db.commit()
    return None
