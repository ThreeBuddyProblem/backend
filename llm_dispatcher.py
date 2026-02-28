"""Small helper that calls the local LLM HTTP API to generate recommendations
from a list of diary entries.

Usage:
    from llm_dispatcher import generate_recommendations

    recs = generate_recommendations(diary_entries)
    # recs is a list of dicts: [{"severity": 0, "title": "...", "message": "..."}, ...]
"""
import json
import re
from typing import List, Dict
import logging
import requests

logger = logging.getLogger(__name__)


def _build_prompt(entries: List[Dict]) -> str:
    lines = []
    for i, e in enumerate(entries, start=1):
        lines.append(f"Entry #{i}:")
        ts = e.get("timestamp") or e.get("date") or "<no timestamp>"
        lines.append(f"  timestamp: {ts}")
        if "moodLevel" in e:
            lines.append(f"  moodLevel: {e.get('moodLevel')}")
        if "emotions" in e and e.get("emotions"):
            lines.append(f"  emotions: {', '.join(e.get('emotions'))}")
        if e.get("healthComplaints"):
            lines.append(f"  healthComplaints: {e.get('healthComplaints')}")
        if e.get("foodIntake"):
            lines.append(f"  foodIntake: {e.get('foodIntake')}")
        if e.get("notes"):
            lines.append(f"  notes: {e.get('notes')}")

    entries_block = "\n".join(lines)

    return f"""You are a health assistant. Analyze these diary entries and produce health recommendations grouped by symptom or health category.

{entries_block}

Return ONLY a JSON array (no markdown, no explanation). Each element must be:
{{"severity": <0|1|2>, "title": "<short category title>", "message": "<concise recommendation>"}}

Severity levels: 0 = informational, 1 = warning, 2 = urgent.

Rules:
- Group related symptoms/complaints together into one recommendation, so look for relations between entries.
- Do NOT necessarily create one recommendation per diary entry, only if needed.
- Do NOT necessarily lump everything into a single recommendation either, only if needed.
- Be concise yet precise.
- Give actual useful recommendations, not generic advice.
- Give your recommendations from the perspective of a doctor talking to a patient, so directly to the person who wrote the diary entries.
- Try to set severity based on the possible health impact on the patient.
- If new entries make the previous recommendations obsolete, remove the previous recommendations.
- If the new entries are identical in content to the previous entries, do not create or modify recommendations.
- Return valid JSON only."""


def generate_recommendations(
    entries: List[Dict],
    model: str = "gemma3:4b",
    api_url: str = "http://192.168.73.139:11434/api/generate",
    timeout: float = 30.0,
) -> List[Dict]:
    if not isinstance(entries, list):
        raise ValueError("entries must be a list of dict-like diary entries")

    prompt = _build_prompt(entries)
    payload = {"model": model, "prompt": prompt, "stream": False}

    logger.debug("Sending LLM request to %s with model=%s", api_url, model)
    try:
        resp = requests.post(api_url, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        logger.exception("LLM request failed: %s", exc)
        raise

    if not resp.ok:
        msg = f"LLM API returned {resp.status_code}: {resp.text}"
        logger.error(msg)
        resp.raise_for_status()

    try:
        body = resp.json()
    except ValueError:
        logger.error("LLM returned non-JSON response: %s", resp.text)
        raise

    raw_text = body.get("response", "")

    # Extract JSON array from the response text
    match = re.search(r"\[.*\]", raw_text, re.DOTALL)
    if not match:
        raise ValueError(f"LLM did not return a JSON array: {raw_text!r}")

    recommendations = json.loads(match.group())
    if not isinstance(recommendations, list):
        raise ValueError(f"Expected a JSON array, got: {type(recommendations)}")

    return recommendations


def _extract_text_from_body(body: Dict) -> str:
    # Try common fields for textual output
    if not body:
        return ""
    if isinstance(body, str):
        return body
    for k in ("response", "text", "output", "result", "completion", "content"):
        v = body.get(k)
        if isinstance(v, str) and v.strip():
            return v
    # choices/outputs style
    choices = body.get("choices") or body.get("outputs")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            for k in ("text", "message", "content"):
                v = first.get(k)
                if isinstance(v, str) and v.strip():
                    return v
    # fallback to JSON string
    try:
        return json.dumps(body)
    except Exception:
        return str(body)


def generate_summary(
    entries: List[Dict],
    model: str = "gemma3:4b",
    api_url: str = "http://192.168.73.139:11434/api/generate",
    timeout: float = 30.0,
) -> str:
    """Generate a short subjective-summary (SOAP 'S' component) from diary entries.

    Returns a concise paragraph (2-4 sentences) summarizing the patient's subjective
    health complaints, focusing on symptoms, onset, severity, frequency and relevant
    contextual details (food intake, emotions) to be used as the subjective part of
    a SOAP note.
    """
    if not isinstance(entries, list):
        raise ValueError("entries must be a list of dict-like diary entries")

    # Build a compact prompt that emphasizes subjective complaints
    lines = [
        "You are a clinical scribe. Write a concise subjective (S) section for a SOAP note",
        "based on the following patient diary entries. Focus on the patient's complaints,",
        "their onset, severity, frequency, any triggers or relieving factors, and relevant",
        "context such as food intake or emotions. Produce a single short paragraph (2-4",
        "sentences) suitable for clinical documentation. Do NOT include recommendations",
        "or plan details. Be factual and use clinical-style wording.",
    ]

    for i, e in enumerate(entries, start=1):
        ts = e.get("timestamp") or e.get("date") or "<no timestamp>"
        lines.append(f"Entry #{i} ({ts}):")
        if e.get("healthComplaints"):
            lines.append(f"  complaints: {e.get('healthComplaints')}")
        if e.get("foodIntake"):
            lines.append(f"  food: {e.get('foodIntake')}")
        if e.get("notes"):
            lines.append(f"  notes: {e.get('notes')}")
        if e.get("emotions"):
            lines.append(f"  emotions: {', '.join(e.get('emotions'))}")

    prompt = "\n".join(lines)

    payload = {"model": model, "prompt": prompt, "stream": False}

    logger.debug("Sending LLM summary request to %s with model=%s", api_url, model)
    try:
        resp = requests.post(api_url, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        logger.exception("LLM request failed: %s", exc)
        raise

    if not resp.ok:
        msg = f"LLM API returned {resp.status_code}: {resp.text}"
        logger.error(msg)
        resp.raise_for_status()

    try:
        body = resp.json()
    except ValueError:
        logger.error("LLM returned non-JSON response: %s", resp.text)
        raise

    text = _extract_text_from_body(body)

    # Clean up text: strip leading/trailing whitespace and remove surrounding quotes
    summary = text.strip()
    if summary.startswith('"') and summary.endswith('"'):
        summary = summary[1:-1].strip()

    # Ensure the summary is short: if LLM returned multiple paragraphs, keep first paragraph
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", summary) if p.strip()]
    if paragraphs:
        summary = paragraphs[0]

    # Limit length to ~400 characters to keep it concise
    if len(summary) > 400:
        summary = summary[:397].rstrip() + "..."

    return summary
