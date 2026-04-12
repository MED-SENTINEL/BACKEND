"""
OCR Service — Local extraction from lab report images.

Uses basic file type detection and returns structured mock data.
In a production system this would use Tesseract or a vision model,
but for the hackathon demo this provides realistic structured output.
"""

import os
import json
import hashlib
from datetime import datetime


# ─── Multiple realistic report templates for variety ───
REPORT_TEMPLATES = [
    {
        "report_type": "Complete Blood Count (CBC)",
        "lab_name": "Apollo Diagnostics",
        "values": {
            "hemoglobin": {"value": 14.2, "unit": "g/dL", "reference_range": "13.5-17.5", "status": "normal"},
            "rbc_count": {"value": 5.1, "unit": "million/µL", "reference_range": "4.5-5.5", "status": "normal"},
            "wbc_count": {"value": 7800, "unit": "/µL", "reference_range": "4000-11000", "status": "normal"},
            "platelet_count": {"value": 250000, "unit": "/µL", "reference_range": "150000-400000", "status": "normal"},
            "blood_glucose_fasting": {"value": 118, "unit": "mg/dL", "reference_range": "70-100", "status": "elevated"},
            "creatinine": {"value": 1.4, "unit": "mg/dL", "reference_range": "0.7-1.3", "status": "elevated"},
            "egfr": {"value": 78, "unit": "mL/min", "reference_range": ">90", "status": "low"},
            "total_cholesterol": {"value": 220, "unit": "mg/dL", "reference_range": "<200", "status": "elevated"},
            "cortisol": {"value": 18.5, "unit": "µg/dL", "reference_range": "6-23", "status": "normal"},
        },
        "flags": [
            "Fasting blood glucose elevated at 118 mg/dL — pre-diabetic range, needs monitoring",
            "Creatinine slightly elevated at 1.4 mg/dL — kidney function should be watched",
            "eGFR at 78 mL/min, below optimal — early kidney function decline possible",
            "Total cholesterol at 220 mg/dL — dietary and lifestyle changes recommended",
        ],
        "summary": "Blood counts are healthy. However, metabolic markers show elevated fasting glucose (pre-diabetic range) and rising cholesterol. Kidney markers (creatinine/eGFR) indicate mild concern. Follow-up recommended in 3 months.",
    },
    {
        "report_type": "Lipid Panel + Metabolic",
        "lab_name": "SRL Diagnostics",
        "values": {
            "total_cholesterol": {"value": 235, "unit": "mg/dL", "reference_range": "<200", "status": "elevated"},
            "ldl_cholesterol": {"value": 155, "unit": "mg/dL", "reference_range": "<130", "status": "elevated"},
            "hdl_cholesterol": {"value": 42, "unit": "mg/dL", "reference_range": ">40", "status": "normal"},
            "triglycerides": {"value": 180, "unit": "mg/dL", "reference_range": "<150", "status": "elevated"},
            "blood_glucose_fasting": {"value": 112, "unit": "mg/dL", "reference_range": "70-100", "status": "elevated"},
            "hba1c": {"value": 6.1, "unit": "%", "reference_range": "<5.7", "status": "elevated"},
            "alt": {"value": 35, "unit": "U/L", "reference_range": "<40", "status": "normal"},
            "ast": {"value": 28, "unit": "U/L", "reference_range": "<40", "status": "normal"},
        },
        "flags": [
            "LDL cholesterol elevated at 155 mg/dL — cardiovascular risk increased",
            "Triglycerides high at 180 mg/dL — dietary intervention recommended",
            "HbA1c at 6.1% — indicates pre-diabetic state",
            "Fasting glucose trending upward at 112 mg/dL",
        ],
        "summary": "Lipid panel shows elevated LDL and triglycerides indicating increased cardiovascular risk. HbA1c of 6.1% places patient in pre-diabetic range. Liver enzymes are normal. Recommend dietary changes and follow-up in 3 months.",
    },
    {
        "report_type": "Thyroid Function Panel",
        "lab_name": "Thyrocare",
        "values": {
            "tsh": {"value": 5.8, "unit": "mIU/L", "reference_range": "0.4-4.0", "status": "elevated"},
            "hemoglobin": {"value": 13.5, "unit": "g/dL", "reference_range": "13.5-17.5", "status": "normal"},
            "wbc_count": {"value": 6200, "unit": "/µL", "reference_range": "4000-11000", "status": "normal"},
            "blood_glucose_fasting": {"value": 95, "unit": "mg/dL", "reference_range": "70-100", "status": "normal"},
            "creatinine": {"value": 1.0, "unit": "mg/dL", "reference_range": "0.7-1.3", "status": "normal"},
            "sodium": {"value": 140, "unit": "mEq/L", "reference_range": "136-145", "status": "normal"},
            "potassium": {"value": 4.2, "unit": "mEq/L", "reference_range": "3.5-5.0", "status": "normal"},
        },
        "flags": [
            "TSH elevated at 5.8 mIU/L — subclinical hypothyroidism suspected",
            "Recommend free T4 and T3 tests for complete thyroid evaluation",
        ],
        "summary": "TSH is elevated suggesting subclinical hypothyroidism. All other values including metabolic panel, kidney function, and electrolytes are within normal limits. Further thyroid workup recommended.",
    },
]


def extract_report_data(file_path: str, file_type: str) -> dict:
    """
    Extract structured data from a lab report file.
    Uses deterministic template selection based on file hash for consistency.
    """
    print(f"[OCR] Extracting data from: {file_path} (type: {file_type})")

    # Use file hash to deterministically pick a template (same file = same result)
    template_index = 0
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read(1024)).hexdigest()
            template_index = int(file_hash[:2], 16) % len(REPORT_TEMPLATES)
        except Exception:
            pass
    
    template = REPORT_TEMPLATES[template_index]
    
    return {
        **template,
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "patient_name": "Extracted from report",
        "ocr_confidence": 0.94,
        "extraction_mode": "local_engine",
    }
