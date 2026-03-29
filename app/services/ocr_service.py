"""
OCR Service for lab report extraction.
In development mode, returns mock extracted data.
Set USE_LIVE_OCR=True in config to use the real Gemini API (not implemented yet).
"""

from app.core.config import settings


def extract_report_data(file_path: str, file_type: str) -> dict:
    """
    Extract structured data from a lab report file.

    Args:
        file_path: Path to the uploaded file on disk.
        file_type: File extension ("pdf", "jpg", "png").

    Returns:
        Dictionary with extracted lab values.
    """

    if settings.USE_LIVE_OCR:
        # TODO: Sprint 7+ — Integrate Gemini 2.0 Flash API here
        raise NotImplementedError("Live OCR not implemented yet. Set USE_LIVE_OCR=False in config.")

    # ─── Mock extraction: return fake lab data ───
    print(f"[OCR] Mock extracting data from: {file_path} (type: {file_type})")

    mock_data = {
        "report_type": "Complete Blood Count (CBC)",
        "lab_name": "Apollo Diagnostics",
        "report_date": "2024-12-15",
        "patient_name": "Extracted from report",
        "values": {
            "hemoglobin": {"value": 14.2, "unit": "g/dL", "reference_range": "13.5-17.5", "status": "normal"},
            "rbc_count": {"value": 5.1, "unit": "million/µL", "reference_range": "4.5-5.5", "status": "normal"},
            "wbc_count": {"value": 7800, "unit": "/µL", "reference_range": "4000-11000", "status": "normal"},
            "platelet_count": {"value": 250000, "unit": "/µL", "reference_range": "150000-400000", "status": "normal"},
            "blood_glucose_fasting": {"value": 105, "unit": "mg/dL", "reference_range": "70-100", "status": "elevated"},
            "creatinine": {"value": 1.1, "unit": "mg/dL", "reference_range": "0.7-1.3", "status": "normal"},
            "egfr": {"value": 88, "unit": "mL/min", "reference_range": ">90", "status": "slightly_low"},
            "total_cholesterol": {"value": 210, "unit": "mg/dL", "reference_range": "<200", "status": "elevated"},
            "cortisol": {"value": 18.5, "unit": "µg/dL", "reference_range": "6-23", "status": "normal"},
        },
        "flags": [
            "Blood glucose fasting slightly elevated — consider monitoring",
            "eGFR slightly below reference — kidney function to be watched",
            "Total cholesterol above 200 — lifestyle modifications recommended",
        ],
        "ocr_confidence": 0.92,
        "extraction_mode": "mock",
    }

    return mock_data
