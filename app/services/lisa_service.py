"""
LISA — SENTINEL's AI-Powered Virtual Physician Agent.

Uses GitHub Models (GPT-4o-mini) / Gemini as the AI brain.
Enriches prompts with the patient's actual medical data.
Falls back to local rule-based responses if AI is unavailable.
"""

import json
from typing import Dict, List, Any

from app.services.gemini_client import generate_text


# ─── System Prompt for the LLM ───
LISA_SYSTEM_PROMPT = """You are Dr. LISA, an AI Virtual Physician integrated into the SENTINEL Medical Platform.

ROLE: You are a caring, thorough, and highly knowledgeable medical consultant. You speak like a real doctor reviewing a patient's chart — professional but empathetic.

BEHAVIOR RULES:
1. ALWAYS base your analysis on the patient's ACTUAL data provided below. Never invent or hallucinate values.
2. Provide DETAILED clinical reasoning — explain what each abnormal value means, what organ system it affects, and what conditions it may indicate.
3. When discussing risks, explain the mechanism (e.g., "Elevated ALT suggests hepatocyte damage, which can occur in fatty liver disease, hepatitis, or medication-induced liver injury").
4. Always suggest specific next steps: which tests to repeat, which specialists to see, lifestyle changes.
5. Cross-reference lab values with trauma history when relevant.
6. End every response with a disclaimer that you are an AI assistant and findings should be confirmed with a real physician.
7. Use markdown formatting: **bold** for emphasis, bullet points for lists, headers for sections.
8. Be thorough — give long, detailed, clinically useful responses. Never give one-line answers.
9. If the patient has no data on file, guide them on how to enter their bloodwork or log trauma.

FORMAT: Use clear sections with headers. Include relevant emoji for visual clarity (⚠️ for warnings, ✅ for normal, 🚨 for critical, 🩺 for assessments)."""


def _build_patient_context(patient_data: Dict[str, Any]) -> str:
    """Build a comprehensive patient context string for the LLM prompt."""
    parts = []

    # Profile
    profile = patient_data.get("profile")
    if profile:
        parts.append(f"PATIENT PROFILE: Name: {profile.get('full_name', '?')}, Age: {profile.get('age', '?')}, Gender: {profile.get('gender', '?')}, Blood Type: {profile.get('blood_type', '?')}")
        if profile.get("allergies"):
            parts.append(f"ALLERGIES: {profile['allergies']}")
        if profile.get("chronic_conditions"):
            parts.append(f"CHRONIC CONDITIONS: {profile['chronic_conditions']}")
        if profile.get("current_medications"):
            parts.append(f"CURRENT MEDICATIONS: {profile['current_medications']}")

    # Lab Values
    extractions = patient_data.get("extractions", [])
    if extractions:
        parts.append(f"\nLAB PANELS ON FILE: {len(extractions)}")
        for i, ext in enumerate(extractions):
            if isinstance(ext, str):
                try:
                    ext = json.loads(ext)
                except json.JSONDecodeError:
                    continue
            values = ext.get("values", {})
            if values:
                parts.append(f"\nPanel {i+1} (Date: {ext.get('report_date', '?')}, Type: {ext.get('report_type', '?')}):")
                for test_name, data in values.items():
                    display = test_name.replace("_", " ").title()
                    status = data.get("status", "normal")
                    flag = " ⚠️ FLAGGED" if status != "normal" else ""
                    parts.append(f"  - {display}: {data.get('value')} {data.get('unit', '')} (Ref: {data.get('reference_range', '?')}) [{status}]{flag}")
            flags = ext.get("flags", [])
            if flags:
                parts.append(f"  Observations: {', '.join(flags)}")
    else:
        parts.append("\nLAB DATA: No lab panels on file.")

    # Trauma Pins
    traumas = patient_data.get("trauma_pins", [])
    if traumas:
        parts.append(f"\nTRAUMA RECORDS: {len(traumas)} entries")
        for t in traumas:
            region = t.get("body_region", "?")
            ttype = t.get("trauma_type", "?").replace("_", " ").title()
            severity = t.get("severity", "?")
            notes = t.get("description") or t.get("notes", "")
            parts.append(f"  - {region}: {ttype} (Severity: {severity}){f' — {notes}' if notes else ''}")
    else:
        parts.append("\nTRAUMA RECORDS: None on file.")

    # Insights
    insights = patient_data.get("insights")
    if insights:
        parts.append(f"\nPREVIOUS AI RISK ASSESSMENT: Risk Level = {insights.get('risk_level', '?')}")

    return "\n".join(parts)


def _build_patient_summary(patient_data: Dict[str, Any]) -> Dict:
    """Build a structured summary for the local fallback."""
    summary = {
        "total_reports": 0,
        "abnormal_values": [],
        "normal_values": [],
        "all_values": [],
        "all_flags": [],
        "trauma_count": 0,
        "traumas": [],
        "risk_level": "Unknown",
    }

    extractions = patient_data.get("extractions", [])
    summary["total_reports"] = len(extractions)

    for ext in extractions:
        if isinstance(ext, str):
            try:
                ext = json.loads(ext)
            except json.JSONDecodeError:
                continue
        values = ext.get("values", {})
        for test_name, data in values.items():
            display = test_name.replace("_", " ").title()
            entry = {
                "name": display,
                "value": data.get("value"),
                "unit": data.get("unit", ""),
                "reference": data.get("reference_range", "?"),
                "status": data.get("status", "normal"),
            }
            summary["all_values"].append(entry)
            if data.get("status") != "normal":
                summary["abnormal_values"].append(entry)
            else:
                summary["normal_values"].append(entry)
        summary["all_flags"].extend(ext.get("flags", []))

    traumas = patient_data.get("trauma_pins", [])
    summary["trauma_count"] = len(traumas)
    summary["traumas"] = traumas

    insights = patient_data.get("insights")
    if insights:
        summary["risk_level"] = insights.get("risk_level", "Unknown")

    return summary


def _format_value(entry: Dict) -> str:
    """Format a lab value for display."""
    emoji = {"normal": "✅", "elevated": "⚠️", "low": "⬇️", "critical": "🚨"}.get(entry["status"], "❓")
    return f"{emoji} {entry['name']}: {entry['value']} {entry['unit']} (Ref: {entry['reference']}) [{entry['status']}]"


def _local_fallback(message: str, patient_data: Dict[str, Any]) -> str:
    """Rule-based fallback when AI APIs are unavailable."""
    summary = _build_patient_summary(patient_data)

    if summary["total_reports"] == 0 and summary["trauma_count"] == 0:
        return (
            "I currently have no lab results or trauma history in your chart.\n\n"
            "Please enter your bloodwork on the **Bloodwork** page or log injuries on the **3D Bio-Twin** page.\n\n"
            "⚕️ *I am an AI health assistant. Please confirm with your physician.*"
        )

    response = f"📋 **Dr. LISA — Chart Review** *(offline mode)*\n\n"
    response += f"Data: {summary['total_reports']} panel(s), {len(summary['all_values'])} biomarkers, {summary['trauma_count']} trauma(s)\n\n"

    if summary["abnormal_values"]:
        response += f"**⚠️ Flagged Values ({len(summary['abnormal_values'])}):**\n"
        for v in summary["abnormal_values"]:
            response += f"  {_format_value(v)}\n"
        response += "\n"

    if summary["normal_values"]:
        response += f"**✅ Normal ({len(summary['normal_values'])}):**\n"
        for v in summary["normal_values"][:5]:
            response += f"  ✅ {v['name']}: {v['value']} {v['unit']}\n"
        if len(summary["normal_values"]) > 5:
            response += f"  ...and {len(summary['normal_values']) - 5} more\n"
        response += "\n"

    if summary["trauma_count"] > 0:
        response += f"**🏥 Trauma Records:**\n"
        for t in summary["traumas"]:
            response += f"  • {t.get('body_region', '?')} — {t.get('trauma_type', '?')} ({t.get('severity', '?')})\n"
        response += "\n"

    response += "⚕️ *AI APIs unavailable — showing local analysis. Please confirm with your physician.*"
    return response


def chat(message: str, patient_data: Dict[str, Any]) -> str:
    """
    Process a LISA chat message with patient context.
    Uses GitHub Models / Gemini as primary AI, local fallback if unavailable.
    """
    # Build the patient context
    context = _build_patient_context(patient_data)

    # Build the prompt
    user_prompt = f"""PATIENT MEDICAL DATA:
{context}

PATIENT'S QUESTION: {message}

Please provide a thorough, detailed clinical response based on the patient's actual data above."""

    try:
        # Call the AI engine
        response = generate_text(user_prompt, system_instruction=LISA_SYSTEM_PROMPT)

        # Sanity check — if the AI just echoed the prompt back (local fallback), use rule-based
        if response.strip() == user_prompt.strip():
            return _local_fallback(message, patient_data)

        return response
    except Exception as e:
        print(f"[LISA] AI call failed: {e}")
        return _local_fallback(message, patient_data)
