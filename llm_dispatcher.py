"""Small helper that calls the local LLM HTTP API to generate recommendations
from a list of diary entries.

Usage:
    from llm_dispatcher import generate_recommendation_from_entries

    resp = generate_recommendation_from_entries(diary_entries)
    # resp is the parsed JSON returned by the LLM endpoint
"""
from typing import List, Dict, Optional
import logging
import requests

logger = logging.getLogger(__name__)


def _build_prompt_from_entries(entries: List[Dict]) -> str:
    """Create a human-readable prompt summarizing diary entries.

    The LLM will be asked to produce one short recommendation that takes
    mood, healthComplaints and foodIntake into account.
    """
    lines = [
        "You are a helpful health assistant. Given the following diary entries,"
        " provide a single concise recommendation (1-3 short bullet points)"
        " that considers mood, health complaints, and food intake."
    ]

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
            # keep notes short in the prompt
            note = e.get("notes")
            lines.append(f"  notes: {note}")

    lines.append("")
    lines.append("Please provide:")
    lines.append("- a short recommendation (1-3 bullets) with actionable steps")
    lines.append("- any potential health concerns to watch for")
    lines.append("- one suggested next action the patient can take now, if applicable (the health concerns may not always lead to a next action)")

    return "\n".join(lines)


def generate_recommendation_from_entries(
    entries: List[Dict],
    model: str = "gemma3:4b",
    api_url: str = "http://192.168.73.139:11434/api/generate",
    timeout: float = 30.0,
) -> Dict:
    """Call the LLM API with a generated prompt from diary entries.

    Returns the parsed JSON response from the LLM endpoint. Raises
    requests.HTTPError on non-2xx responses, or requests.RequestException on
    network errors.
    """
    if not isinstance(entries, list):
        raise ValueError("entries must be a list of dict-like diary entries")

    prompt = _build_prompt_from_entries(entries)

    payload = {"model": model, "prompt": prompt, "stream": False}

    logger.debug("Sending LLM request to %s with model=%s", api_url, model)
    try:
        resp = requests.post(api_url, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        logger.exception("LLM request failed: %s", exc)
        raise

    if not resp.ok:
        # raise an informative HTTPError with body included
        msg = f"LLM API returned {resp.status_code}: {resp.text}"
        logger.error(msg)
        resp.raise_for_status()

    try:
        return resp.json()
    except ValueError:
        # not a JSON response
        logger.error("LLM returned non-JSON response: %s", resp.text)
        raise
