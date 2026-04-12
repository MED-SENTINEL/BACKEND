"""
Anomaly Sentinel Agent — Detects dangerous values and clinically significant trends.

Two detection tiers:
1. Threshold-based: Instant checks against medical reference ranges
2. Statistical trend detection: Detects worsening patterns across reports

100% local — no external API calls.
"""

import json
from typing import List, Dict, Any


# ─── Medical Reference Thresholds (Critical Ranges) ───
CRITICAL_THRESHOLDS = {
    "hemoglobin":              {"critical_low": 7.0,  "low": 12.0, "high": 17.5, "critical_high": 20.0, "unit": "g/dL", "organ": "blood"},
    "wbc_count":               {"critical_low": 2000, "low": 4000, "high": 11000, "critical_high": 30000, "unit": "/µL", "organ": "immune"},
    "platelet_count":          {"critical_low": 50000,"low": 150000,"high": 400000,"critical_high": 1000000, "unit": "/µL", "organ": "blood"},
    "blood_glucose_fasting":   {"critical_low": 40,   "low": 70,   "high": 100,  "critical_high": 300, "unit": "mg/dL", "organ": "metabolic"},
    "blood_glucose_random":    {"critical_low": 40,   "low": 70,   "high": 140,  "critical_high": 400, "unit": "mg/dL", "organ": "metabolic"},
    "hba1c":                   {"critical_low": None, "low": None, "high": 5.7,  "critical_high": 9.0, "unit": "%", "organ": "metabolic"},
    "creatinine":              {"critical_low": None, "low": 0.6,  "high": 1.3,  "critical_high": 4.0, "unit": "mg/dL", "organ": "kidney"},
    "egfr":                    {"critical_low": 15,   "low": 60,   "high": None, "critical_high": None, "unit": "mL/min", "organ": "kidney"},
    "bun":                     {"critical_low": None, "low": 7,    "high": 20,   "critical_high": 50, "unit": "mg/dL", "organ": "kidney"},
    "total_cholesterol":       {"critical_low": None, "low": None, "high": 200,  "critical_high": 300, "unit": "mg/dL", "organ": "cardiac"},
    "ldl_cholesterol":         {"critical_low": None, "low": None, "high": 130,  "critical_high": 190, "unit": "mg/dL", "organ": "cardiac"},
    "hdl_cholesterol":         {"critical_low": None, "low": 40,   "high": None, "critical_high": None, "unit": "mg/dL", "organ": "cardiac"},
    "triglycerides":           {"critical_low": None, "low": None, "high": 150,  "critical_high": 500, "unit": "mg/dL", "organ": "cardiac"},
    "potassium":               {"critical_low": 2.5,  "low": 3.5,  "high": 5.0,  "critical_high": 6.5, "unit": "mEq/L", "organ": "cardiac"},
    "sodium":                  {"critical_low": 120,  "low": 136,  "high": 145,  "critical_high": 155, "unit": "mEq/L", "organ": "metabolic"},
    "alt":                     {"critical_low": None, "low": None, "high": 40,   "critical_high": 200, "unit": "U/L", "organ": "liver"},
    "ast":                     {"critical_low": None, "low": None, "high": 40,   "critical_high": 200, "unit": "U/L", "organ": "liver"},
    "tsh":                     {"critical_low": None, "low": 0.4,  "high": 4.0,  "critical_high": 10.0, "unit": "mIU/L", "organ": "thyroid"},
    "cortisol":                {"critical_low": None, "low": 6,    "high": 23,   "critical_high": 35, "unit": "µg/dL", "organ": "endocrine"},
    "rbc_count":               {"critical_low": 2.5,  "low": 4.0,  "high": 5.5,  "critical_high": 7.0, "unit": "million/µL", "organ": "blood"},
}


def check_thresholds(extracted_values: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Tier 1: Instant threshold-based anomaly detection.
    """
    alerts = []

    for test_name, test_data in extracted_values.items():
        if test_name not in CRITICAL_THRESHOLDS:
            continue

        thresholds = CRITICAL_THRESHOLDS[test_name]
        value = test_data.get("value")
        if value is None:
            continue
        
        try:
            value = float(value)
        except (ValueError, TypeError):
            continue

        display_name = test_name.replace("_", " ").title()

        if thresholds.get("critical_low") and value <= thresholds["critical_low"]:
            alerts.append({
                "severity": "critical",
                "title": f"Critically Low {display_name}",
                "body": f"Your {display_name} is {value} {thresholds['unit']}, which is critically below the safe range. Seek immediate medical attention.",
                "organ_system": thresholds["organ"],
                "test": test_name,
                "value": value,
                "unit": thresholds["unit"],
            })
        elif thresholds.get("critical_high") and value >= thresholds["critical_high"]:
            alerts.append({
                "severity": "critical",
                "title": f"Critically High {display_name}",
                "body": f"Your {display_name} is {value} {thresholds['unit']}, which is critically above the safe range. Seek immediate medical attention.",
                "organ_system": thresholds["organ"],
                "test": test_name,
                "value": value,
                "unit": thresholds["unit"],
            })
        elif thresholds.get("low") and value < thresholds["low"]:
            alerts.append({
                "severity": "warning",
                "title": f"Low {display_name}",
                "body": f"Your {display_name} is {value} {thresholds['unit']}, below the normal range of {thresholds['low']}-{thresholds.get('high', '?')} {thresholds['unit']}.",
                "organ_system": thresholds["organ"],
                "test": test_name,
                "value": value,
                "unit": thresholds["unit"],
            })
        elif thresholds.get("high") and value > thresholds["high"]:
            alerts.append({
                "severity": "warning",
                "title": f"Elevated {display_name}",
                "body": f"Your {display_name} is {value} {thresholds['unit']}, above the normal range of {thresholds.get('low', '?')}-{thresholds['high']} {thresholds['unit']}.",
                "organ_system": thresholds["organ"],
                "test": test_name,
                "value": value,
                "unit": thresholds["unit"],
            })

    return alerts


def analyze_trends_local(historical_data: List[Dict]) -> List[Dict[str, str]]:
    """
    Tier 2: Local statistical trend detection across multiple reports.
    No API calls — uses simple comparison logic.
    """
    if len(historical_data) < 2:
        return []

    trend_alerts = []
    value_history = {}

    for ext in historical_data:
        values = ext.get("values", {})
        for test_name, data in values.items():
            val = data.get("value")
            if val is not None:
                try:
                    value_history.setdefault(test_name, []).append(float(val))
                except (ValueError, TypeError):
                    pass

    for test_name, vals in value_history.items():
        if len(vals) < 2 or test_name not in CRITICAL_THRESHOLDS:
            continue

        thresholds = CRITICAL_THRESHOLDS[test_name]
        display_name = test_name.replace("_", " ").title()

        # Detect consistently worsening trend
        is_rising = all(vals[i] < vals[i+1] for i in range(len(vals)-1))
        is_falling = all(vals[i] > vals[i+1] for i in range(len(vals)-1))

        if is_rising and thresholds.get("high"):
            if vals[-1] > thresholds["high"] * 0.85:  # Approaching or exceeding
                trend_alerts.append({
                    "severity": "warning",
                    "title": f"Rising {display_name} Trend",
                    "body": f"{display_name} has been consistently rising: {' → '.join(str(v) for v in vals)}. Current value is approaching or exceeding the upper limit of {thresholds['high']} {thresholds['unit']}.",
                    "organ_system": thresholds["organ"],
                })

        if is_falling and thresholds.get("low"):
            if vals[-1] < thresholds["low"] * 1.15:  # Approaching or below
                trend_alerts.append({
                    "severity": "warning",
                    "title": f"Declining {display_name} Trend",
                    "body": f"{display_name} has been consistently declining: {' → '.join(str(v) for v in vals)}. Current value is approaching or below the lower limit of {thresholds['low']} {thresholds['unit']}.",
                    "organ_system": thresholds["organ"],
                })

    return trend_alerts


def run_anomaly_check(current_extraction: Dict, historical_extractions: List[Dict] = None) -> List[Dict]:
    """
    Full anomaly pipeline: threshold check + local trend analysis.
    """
    alerts = []

    # Tier 1: Instant threshold check
    values = current_extraction.get("values", {})
    threshold_alerts = check_thresholds(values)
    alerts.extend(threshold_alerts)

    # Tier 2: Local trend analysis (if we have history)
    if historical_extractions and len(historical_extractions) >= 2:
        trend_alerts = analyze_trends_local(historical_extractions)
        alerts.extend(trend_alerts)

    # Sort: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a.get("severity", "info"), 3))

    return alerts
