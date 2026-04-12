"""
Health Insight Engine — Local rule-based analysis.

Analyzes patient lab data using medical reference ranges to generate:
- Overall risk assessment (LOW/MEDIUM/HIGH)
- Organ-specific risk scores
- Trend narratives
- Actionable recommendations

No external API calls — 100% local logic.
"""

import json
from typing import Dict, List, Any


# ─── Organ mapping for tests ───
TEST_ORGAN_MAP = {
    "hemoglobin": "blood", "rbc_count": "blood", "wbc_count": "blood", "platelet_count": "blood",
    "blood_glucose_fasting": "metabolic", "blood_glucose_random": "metabolic", "hba1c": "metabolic",
    "creatinine": "kidney", "egfr": "kidney", "bun": "kidney",
    "total_cholesterol": "cardiac", "ldl_cholesterol": "cardiac", "hdl_cholesterol": "cardiac", "triglycerides": "cardiac", "potassium": "cardiac",
    "alt": "liver", "ast": "liver",
    "tsh": "thyroid",
    "cortisol": "metabolic", "sodium": "metabolic",
}


def _score_from_status(status: str) -> int:
    """Convert a test status to a risk contribution score."""
    return {"normal": 0, "low": 25, "elevated": 30, "critical": 70}.get(status, 0)


def _compute_organ_risks(all_values: Dict[str, Any]) -> Dict:
    """Calculate organ risk scores by aggregating test statuses."""
    organ_scores = {}
    organ_counts = {}
    organ_details = {}

    for test_name, data in all_values.items():
        organ = TEST_ORGAN_MAP.get(test_name)
        if not organ:
            continue
        
        status = data.get("status", "normal")
        score = _score_from_status(status)
        
        organ_scores[organ] = organ_scores.get(organ, 0) + score
        organ_counts[organ] = organ_counts.get(organ, 0) + 1
        
        if status != "normal":
            display = test_name.replace("_", " ").title()
            detail = f"{display}: {data.get('value')} {data.get('unit', '')} ({status})"
            organ_details.setdefault(organ, []).append(detail)

    result = {}
    for organ in ["kidney", "cardiac", "metabolic", "liver", "blood", "thyroid"]:
        count = organ_counts.get(organ, 0)
        if count == 0:
            result[organ] = {"score": 0, "label": "No Data", "detail": "No relevant tests found"}
            continue
        
        avg_score = min(100, organ_scores.get(organ, 0) // count * 2)  # Scale up slightly
        details = organ_details.get(organ, [])
        
        if avg_score >= 70:
            label = "Concern"
        elif avg_score >= 40:
            label = "Attention"
        elif avg_score >= 20:
            label = "Monitor"
        else:
            label = "Healthy"
        
        result[organ] = {
            "score": avg_score,
            "label": label,
            "detail": "; ".join(details) if details else "All values within normal range"
        }
    
    return result


def _detect_trends(extractions: List[Dict]) -> List[str]:
    """Detect trends across multiple reports."""
    if len(extractions) < 2:
        return ["Insufficient data for trend analysis — upload more reports to enable tracking."]
    
    trends = []
    # Track values across reports
    value_history = {}
    for ext in extractions:
        values = ext.get("values", {})
        for test_name, data in values.items():
            val = data.get("value")
            if val is not None:
                value_history.setdefault(test_name, []).append(float(val))
    
    for test_name, vals in value_history.items():
        if len(vals) < 2:
            continue
        display = test_name.replace("_", " ").title()
        
        # Check if consistently rising
        if all(vals[i] < vals[i+1] for i in range(len(vals)-1)):
            trends.append(f"{display} is trending upward: {' → '.join(str(v) for v in vals)}")
        elif all(vals[i] > vals[i+1] for i in range(len(vals)-1)):
            trends.append(f"{display} is trending downward: {' → '.join(str(v) for v in vals)}")
    
    if not trends:
        trends.append("No significant trends detected across your reports. Values appear stable.")
    
    return trends


def _generate_recommendations(organ_risks: Dict, all_flags: List[str]) -> List[str]:
    """Generate actionable recommendations based on organ risks."""
    recs = []
    
    for organ, data in organ_risks.items():
        score = data.get("score", 0)
        if score >= 40:
            if organ == "metabolic":
                recs.append("Monitor blood sugar levels regularly. Consider dietary changes to manage glucose.")
                recs.append("Reduce refined sugar and processed carbohydrate intake.")
            elif organ == "cardiac":
                recs.append("Review cardiovascular markers with your doctor. Consider a heart-healthy diet.")
                recs.append("Increase physical activity — aim for 150 minutes of moderate exercise per week.")
            elif organ == "kidney":
                recs.append("Stay well hydrated and discuss kidney function with your healthcare provider.")
                recs.append("Limit sodium intake and monitor blood pressure regularly.")
            elif organ == "liver":
                recs.append("Discuss liver function results with your doctor. Limit alcohol consumption.")
            elif organ == "thyroid":
                recs.append("Elevated TSH detected. Request complete thyroid panel (T3, T4) from your doctor.")
            elif organ == "blood":
                recs.append("Blood count abnormalities detected. Follow up with a hematologist if persistent.")
    
    if not recs:
        recs.append("All organ systems look healthy! Maintain your current lifestyle and continue regular check-ups.")
        recs.append("Schedule your next health screening in 6-12 months.")
    
    return recs[:6]  # Cap at 6


def _extract_key_findings(all_values: Dict, all_flags: List[str]) -> List[Dict]:
    """Extract key findings from lab values."""
    findings = []
    
    for test_name, data in all_values.items():
        status = data.get("status", "normal")
        if status == "normal":
            continue
        
        display = test_name.replace("_", " ").title()
        severity = "critical" if status == "critical" else "warning" if status in ["elevated", "low"] else "info"
        
        findings.append({
            "finding": f"{display}: {data.get('value')} {data.get('unit', '')}",
            "severity": severity,
            "detail": f"Reference range: {data.get('reference_range', '?')} — Status: {status}"
        })
    
    # Sort by severity
    order = {"critical": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: order.get(f["severity"], 3))
    
    return findings[:10]


def generate_health_insights(patient_data: Dict[str, Any]) -> Dict:
    """
    Generate comprehensive health insights from patient data.
    100% local — no API calls.
    """
    extractions = patient_data.get("extractions", [])
    trauma_pins = patient_data.get("trauma_pins", [])

    if not extractions:
        return _empty_insight("No lab reports available for analysis. Upload a report to get started.")

    # Merge all values from all reports (latest values win)
    all_values = {}
    all_flags = []
    for ext in extractions:
        if isinstance(ext, str):
            try:
                ext = json.loads(ext)
            except json.JSONDecodeError:
                continue
        values = ext.get("values", {})
        all_values.update(values)
        all_flags.extend(ext.get("flags", []))

    # Compute organ risks
    organ_risks = _compute_organ_risks(all_values)

    # Compute overall risk
    scores = [d["score"] for d in organ_risks.values() if d["score"] > 0]
    avg_score = sum(scores) / max(len(scores), 1)
    
    if avg_score >= 50:
        risk_level = "HIGH"
        confidence = min(95, 70 + int(avg_score / 3))
    elif avg_score >= 25:
        risk_level = "MEDIUM"
        confidence = min(90, 65 + int(avg_score / 2))
    else:
        risk_level = "LOW"
        confidence = max(60, 85 - int(avg_score))

    # Count abnormal values
    abnormal_count = sum(1 for v in all_values.values() if v.get("status") != "normal")
    total_count = len(all_values)
    
    # Build summary
    if risk_level == "HIGH":
        summary = f"Analysis of {len(extractions)} report(s) shows {abnormal_count} out of {total_count} values outside normal range. Multiple organ systems require attention. Please consult your healthcare provider promptly."
    elif risk_level == "MEDIUM":
        summary = f"Analysis of {len(extractions)} report(s) reveals {abnormal_count} values requiring monitoring. Some systems show mild deviations that should be tracked over time with follow-up testing."
    else:
        summary = f"Analysis of {len(extractions)} report(s) shows most values within normal limits. Your overall health profile looks good. Continue regular check-ups to maintain your health."

    # Add trauma context
    if trauma_pins:
        summary += f" Note: {len(trauma_pins)} trauma record(s) on file."

    trends = _detect_trends(extractions)
    recommendations = _generate_recommendations(organ_risks, all_flags)
    key_findings = _extract_key_findings(all_values, all_flags)

    return {
        "risk_level": risk_level,
        "confidence": confidence,
        "summary": summary,
        "organ_risks": organ_risks,
        "trends": trends,
        "recommendations": recommendations,
        "key_findings": key_findings,
    }


def _empty_insight(reason: str) -> Dict:
    """Return an empty insight structure when analysis can't be performed."""
    return {
        "risk_level": "LOW",
        "confidence": 0,
        "summary": reason,
        "organ_risks": {
            "kidney": {"score": 0, "label": "No Data", "detail": "No relevant data available"},
            "cardiac": {"score": 0, "label": "No Data", "detail": "No relevant data available"},
            "metabolic": {"score": 0, "label": "No Data", "detail": "No relevant data available"},
            "liver": {"score": 0, "label": "No Data", "detail": "No relevant data available"},
            "blood": {"score": 0, "label": "No Data", "detail": "No relevant data available"},
            "thyroid": {"score": 0, "label": "No Data", "detail": "No relevant data available"},
        },
        "trends": [],
        "recommendations": ["Upload lab reports to enable AI-powered health insights."],
        "key_findings": [],
    }
