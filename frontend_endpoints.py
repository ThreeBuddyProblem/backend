
from flask import Flask, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError
from typing import Dict
from datetime import datetime, timedelta, timezone
import os
import tempfile
import argparse
from dotenv import load_dotenv

import db
from models import DiaryEntryModel, PatientProfileModel, HealthAlertModel, AlertSeverity
from llm_dispatcher import generate_recommendation_from_entries


app = Flask(__name__)
CORS(app)

# The Whisper model should be loaded in a separate process (see `stt_launcher.py`).
# The main backend will forward uploaded audio to that service and will not
# initialize any heavy model locally.

import requests

# Simple in-memory data stores (for demo/dev). Separate stores for entries and profiles.
DIARY_STORE: Dict[str, dict] = {}
PROFILE_STORE: Dict[str, dict] = {}
ALERT_STORE: Dict[str, dict] = {}


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.route("/entries", methods=["POST"])
def create_entry():
    """Create a new diary entry. Validates payload against DiaryEntryModel."""
    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    payload = request.get_json()
    try:
        entry = DiaryEntryModel.parse_obj(payload)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400

    DIARY_STORE[entry.id] = entry.to_json_dict()
    return jsonify(DIARY_STORE[entry.id]), 201


@app.route("/entries/<entry_id>", methods=["GET"])
def get_entry(entry_id: int):
    """Return a single diary entry by id."""
    entry = db.find_diary_entry_by_id(entry_id)
    if entry is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(entry), 200


@app.route("/profiles/<patient_profile_id>/entries", methods=["GET"])
def get_patient_profile_entries(patient_profile_id: int):
    """Return all diary entries of patient by patient profile id."""
    entries = db.find_diary_entries_by_patient_profile_id(patient_profile_id)
    if entries is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(entries), 200


@app.route("/entries/<entry_id>", methods=["PUT"])
def update_entry(entry_id: str):
    """Update an existing diary entry. Merges payload into stored entry and re-validates."""
    if entry_id not in DIARY_STORE:
        return jsonify({"error": "Not found"}), 404

    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    payload = request.get_json()
    # Merge existing stored dict with incoming payload (incoming keys override)
    merged = {**DIARY_STORE[entry_id], **payload}
    try:
        entry = DiaryEntryModel.parse_obj(merged)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400

    DIARY_STORE[entry.id] = entry.to_json_dict()
    return jsonify(DIARY_STORE[entry.id]), 200


@app.route("/entries/<entry_id>", methods=["DELETE"])
def delete_entry(entry_id: str):
    """Delete a diary entry."""
    if entry_id not in DIARY_STORE:
        return jsonify({"error": "Not found"}), 404
    del DIARY_STORE[entry_id]
    return "", 204


## Patient profile endpoints ################################

@app.route("/profiles", methods=["POST"])
def create_profile():
    """Create a new patient profile. Validates payload against PatientProfileModel."""
    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    payload = request.get_json()
    try:
        profile = PatientProfileModel.parse_obj(payload)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400

    PROFILE_STORE[profile.id] = profile.to_json_dict()
    return jsonify(PROFILE_STORE[profile.id]), 201


@app.route("/profiles", methods=["GET"])
def list_profiles():
    """List all patient profiles."""
    return jsonify(db.find_all_patient_profiles()), 200


@app.route("/profiles/<profile_id>", methods=["GET"])
def get_profile(profile_id: int):
    """Return a single profile by id."""
    profile = db.find_patient_profile_by_id(profile_id)
    if profile is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(profile), 200


@app.route("/profiles/<profile_id>", methods=["PUT"])
def update_profile(profile_id: str):
    """Update an existing patient profile. Merges payload into stored profile and re-validates."""
    if profile_id not in PROFILE_STORE:
        return jsonify({"error": "Not found"}), 404

    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    payload = request.get_json()
    merged = {**PROFILE_STORE[profile_id], **payload}
    try:
        profile = PatientProfileModel.parse_obj(merged)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400

    PROFILE_STORE[profile.id] = profile.to_json_dict()
    return jsonify(PROFILE_STORE[profile.id]), 200


@app.route("/profiles/<profile_id>", methods=["DELETE"])
def delete_profile(profile_id: str):
    """Delete a patient profile."""
    if profile_id not in PROFILE_STORE:
        return jsonify({"error": "Not found"}), 404
    del PROFILE_STORE[profile_id]
    return "", 204


## Health alert endpoints ################################

@app.route("/alerts", methods=["POST"])
def create_alert():
    """Create a new health alert. Validates payload against HealthAlertModel."""
    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    payload = request.get_json()
    try:
        alert = HealthAlertModel.parse_obj(payload)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400

    ALERT_STORE[alert.id] = alert.to_json_dict()
    return jsonify(ALERT_STORE[alert.id]), 201


@app.route("/alerts", methods=["GET"])
def list_alerts():
    """List all health alerts."""
    return jsonify(db.find_all_health_alerts()), 200


@app.route("/alerts/<alert_id>", methods=["GET"])
def get_alert(alert_id: int):
    """Return a single alert by id."""
    health_alert = db.find_health_alert_by_id(alert_id)
    if health_alert is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(health_alert), 200


@app.route("/alerts/<alert_id>", methods=["PUT"])
def update_alert(alert_id: str):
    """Update an existing alert. Merges payload into stored alert and re-validates."""
    if alert_id not in ALERT_STORE:
        return jsonify({"error": "Not found"}), 404

    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    payload = request.get_json()
    merged = {**ALERT_STORE[alert_id], **payload}
    try:
        alert = HealthAlertModel.parse_obj(merged)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400

    ALERT_STORE[alert.id] = alert.to_json_dict()
    return jsonify(ALERT_STORE[alert.id]), 200


@app.route("/alerts/<alert_id>", methods=["DELETE"])
def delete_alert(alert_id: str):
    """Delete a health alert."""
    if alert_id not in ALERT_STORE:
        return jsonify({"error": "Not found"}), 404
    del ALERT_STORE[alert_id]
    return "", 204


## Transcription endpoint ################################

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    """Transcribe an uploaded audio file using Whisper.

    Accepts multipart form data with:
      - file: audio file (WAV, m4a, etc.)
      - language: language code (e.g. 'hu', 'en') — optional, defaults to 'hu'

    Returns: {"text": "transcribed text..."}
    """
    # Forward the uploaded audio file to a separately-run STT service
    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["file"]
    stt_url = request.args.get("stt_url") or os.environ.get("STT_URL") or "http://127.0.0.1:11435/transcribe"

    # Read file bytes and forward as multipart/form-data
    try:
        data_bytes = audio_file.read()
        files = {"file": (audio_file.filename or "audio", data_bytes, audio_file.mimetype)}
        # forward language param if provided by the caller
        forward_data = {}
        language = request.form.get("language")
        if language:
            forward_data["language"] = language

        resp = requests.post(stt_url, files=files, data=forward_data or None, timeout=60)
    except requests.RequestException as exc:
        return jsonify({"error": "stt_unreachable", "details": str(exc)}), 502

    try:
        body = resp.json()
    except Exception:
        body = {"error": "stt_non_json_response", "text": resp.text}

    return jsonify({"stt_status": resp.status_code, "stt_response": body}), resp.status_code

@app.route("/profiles/<profile_id>/recommendation", methods=["GET"])
def get_recommendation(patient_profile_id: int):
    """Generate a recommendation from all diary entries using the LLM.

    Optional query parameter: ?model=gemma3:4b
    Returns the raw JSON returned by the LLM endpoint under the `recommendation` key.
    """
    model = request.args.get("model", "gemma3:4b")
    try:
        def _extract_text_from_llm_response(resp):
            # Try common keys to find text in the LLM response JSON
            if resp is None:
                return ""
            if isinstance(resp, str):
                return resp
            if isinstance(resp, dict):
                # common fields
                for k in ("text", "output", "result", "completion", "response", "content"):
                    v = resp.get(k)
                    if isinstance(v, str) and v.strip():
                        return v
                # OpenAI-like choices
                choices = resp.get("choices") or resp.get("outputs")
                if isinstance(choices, list) and len(choices) > 0:
                    first = choices[0]
                    if isinstance(first, dict):
                        for k in ("text", "message", "content"):
                            v = first.get(k)
                            if isinstance(v, str) and v.strip():
                                return v
                # fallback to stringify
                return str(resp)
            return str(resp)

        # Only use entries from the last 30 days (use timezone-aware UTC cutoff)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent_entries = []
        for e in DIARY_STORE.values():
            ts = e.get("timestamp")
            if not ts:
                continue
            # Accept ISO timestamps with or without trailing 'Z'
            try:
                    # normalize string timestamps to a form accepted by fromisoformat
                    if isinstance(ts, str):
                        s = ts
                        if s.endswith("Z"):
                            # replace Z with +00:00 so fromisoformat returns offset-aware datetime
                            s = s.replace("Z", "+00:00")
                        parsed = datetime.fromisoformat(s)
                    elif isinstance(ts, datetime):
                        parsed = ts
                    else:
                        # unexpected type, skip
                        continue
                    # ensure parsed is timezone-aware in UTC for safe comparison
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    else:
                        parsed = parsed.astimezone(timezone.utc)
            except Exception:
                # skip entries with unparsable timestamps
                continue

            if parsed >= cutoff:
                recent_entries.append(e)

        if not recent_entries:
            return jsonify({"error": "no_recent_entries", "details": "No diary entries in the last 30 days."}), 400

        llm_response = generate_recommendation_from_entries(recent_entries, model=model)
    except Exception as exc:
        # Return a 502 to indicate upstream service failure
        return jsonify({"error": "llm_error", "details": str(exc)}), 502

    # Extract human text from LLM response and build a HealthAlert
    text = _extract_text_from_llm_response(llm_response)
    # Parse: first word => severity, next line => title, rest => message
    lines = [ln for ln in text.splitlines() if ln is not None]
    severity_token = ""
    title = ""
    message = ""
    if len(lines) >= 1 and lines[0].strip():
        first_line = lines[0].strip()
        parts = first_line.split()
        if parts:
            # take only alphabetic chars from token
            token = ''.join(ch for ch in parts[0] if ch.isalpha()).lower()
            try:
                severity = AlertSeverity(token)
            except Exception:
                severity = AlertSeverity.info
            severity_token = token
    else:
        severity = AlertSeverity.info

    if len(lines) >= 2:
        title = lines[1].strip()

    if len(lines) >= 3:
        message = "\n".join(lines[2:]).strip()
    else:
        # if there was only one or two lines, use the remaining text as message
        remaining = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        message = remaining or text

    try:
        alert = HealthAlertModel(
            patient_profile_id,
            title or "Recommendation",
            message or text,
            datetime.utcnow(),
            False,
            severity,
        )
        alert = db.insert_health_alert(alert)
    except Exception as exc:
        # If alert creation fails, log and continue returning the recommendation
        return jsonify({"recommendation": llm_response, "alert_error": str(exc)}), 200

    return jsonify({"created_alert": alert.to_json_dict()}), 200

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backend server")
    parser.add_argument("--port", required=False, help="Port of the server", default=5000)
    return parser.parse_args()

if __name__ == "__main__":
    # Useful defaults for local development. In production, run behind a WSGI server.
    args = parse_args()
    load_dotenv()
    db.init_db()
    app.run(host="0.0.0.0", port=args.port, debug=True)
