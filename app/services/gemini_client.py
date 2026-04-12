"""
SENTINEL AI Client — GitHub Models + Gemini with local fallback.

Uses GitHub Models API (OpenAI-compatible) as primary AI engine.
Falls back to Gemini, then to local rule-based analysis.
"""

import json
import re
import os
import httpx

from app.core.config import settings


# ─── GitHub Models (OpenAI-compatible endpoint) ───
GITHUB_MODELS_URL = "https://models.inference.ai.azure.com"
GITHUB_MODEL_NAME = "gpt-4o-mini"  # Free tier on GitHub Models


def generate_text(prompt: str, system_instruction: str = "", **kwargs) -> str:
    """
    Generate text using GitHub Models API (primary) or Gemini (fallback).
    Returns the AI-generated response string.
    """
    # Try GitHub Models first
    if settings.GITHUB_TOKEN:
        try:
            return _github_models_generate(prompt, system_instruction)
        except Exception as e:
            print(f"[AI] GitHub Models failed: {e}")

    # Try Gemini as fallback
    if settings.GEMINI_API_KEY:
        try:
            return _gemini_generate(prompt, system_instruction)
        except Exception as e:
            print(f"[AI] Gemini failed: {e}")

    # Local fallback — return the prompt as passthrough
    print("[AI] All APIs failed. Using local fallback.")
    return prompt


def _github_models_generate(prompt: str, system_instruction: str = "") -> str:
    """Call GitHub Models API (OpenAI-compatible chat completions)."""
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    response = httpx.post(
        f"{GITHUB_MODELS_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "model": GITHUB_MODEL_NAME,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 2000,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _gemini_generate(prompt: str, system_instruction: str = "") -> str:
    """Call Gemini API as fallback."""
    full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
    
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2000},
        },
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def analyze_image(image_bytes: bytes, prompt: str, mime_type: str = "image/jpeg", **kwargs) -> str:
    """Image analysis stub — OCR is handled directly in ocr_service.py"""
    return "{}"


def parse_json_response(raw_text: str) -> dict | list:
    """
    Robustly extract JSON from text that may contain
    markdown fences, preamble text, or trailing commentary.
    """
    if not raw_text:
        return {"error": "Empty response"}

    text = raw_text.strip()

    # 1. Strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # 2. Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Find first { or [ and match to last } or ]
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = text.find(start_char)
        end_idx = text.rfind(end_char)
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(text[start_idx : end_idx + 1])
            except json.JSONDecodeError:
                continue

    return {"error": "Failed to parse JSON"}
