
from flask import Flask, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError

from datetime import datetime, timedelta, timezone
import os
import tempfile
import argparse
from dotenv import load_dotenv

import db
from models import DiaryEntryModel, PatientProfileModel, HealthAlertModel
from llm_dispatcher import generate_recommendations


app = Flask(__name__)
CORS(app)

# The Whisper model should be loaded in a separate process (see `stt_launcher.py`).
# The main backend will forward uploaded audio to that service and will not
# initialize any heavy model locally.

import requests


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

    entry = db.insert_diary_entry(entry)
    return jsonify(entry.id), 201


@app.route("/entries/<entry_id>", methods=["GET"])
def get_entry(entry_id: int):
    """Return a single diary entry by id."""
    entry = db.find_diary_entry_by_id(entry_id)
    if entry is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(entry.to_json_dict()), 200


@app.route("/profiles/<patient_profile_id>/entries", methods=["GET"])
def get_patient_profile_entries(patient_profile_id: int):
    """Return all diary entries of patient by patient profile id."""
    entries = db.find_diary_entries_by_patient_profile_id(patient_profile_id)
    if entries is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify([e.to_json_dict() for e in entries]), 200


@app.route("/entries/<int:entry_id>", methods=["PUT"])
def update_entry(entry_id: int):
    """Update an existing diary entry. Merges payload into stored entry and re-validates."""
    existing = db.find_diary_entry_by_id(entry_id)
    if existing is None:
        return jsonify({"error": "Not found"}), 404

    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    payload = request.get_json()
    merged = {**existing.to_json_dict(), **payload}
    try:
        entry = DiaryEntryModel.parse_obj(merged)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400

    updated = db.update_diary_entry(entry_id, entry)
    return jsonify(updated.to_json_dict()), 200


@app.route("/entries/<int:entry_id>", methods=["DELETE"])
def delete_entry(entry_id: int):
    """Delete a diary entry."""
    if not db.delete_diary_entry(entry_id):
        return jsonify({"error": "Not found"}), 404
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

    profile = db.insert_patient_profile(profile)
    return jsonify(profile.id), 201


@app.route("/profiles", methods=["GET"])
def list_profiles():
    """List all patient profiles."""
    return jsonify([profile.to_json_dict() for profile in db.find_all_patient_profiles()]), 200


@app.route("/profiles/<profile_id>", methods=["GET"])
def get_profile(profile_id: int):
    """Return a single profile by id."""
    profile = db.find_patient_profile_by_id(profile_id)
    if profile is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(profile.to_json_dict()), 200


@app.route("/profiles/<int:profile_id>", methods=["PUT"])
def update_profile(profile_id: int):
    """Update an existing patient profile. Merges payload into stored profile and re-validates."""
    existing = db.find_patient_profile_by_id(profile_id)
    if existing is None:
        return jsonify({"error": "Not found"}), 404

    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    payload = request.get_json()
    merged = {**existing.to_json_dict(), **payload}
    try:
        profile = PatientProfileModel.parse_obj(merged)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400

    updated = db.update_patient_profile(profile_id, profile)
    return jsonify(updated.to_json_dict()), 200


@app.route("/profiles/<int:profile_id>", methods=["DELETE"])
def delete_profile(profile_id: int):
    """Delete a patient profile."""
    if not db.delete_patient_profile(profile_id):
        return jsonify({"error": "Not found"}), 404
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

    alert = db.insert_health_alert(alert)
    return jsonify(alert.id), 201


@app.route("/alerts", methods=["GET"])
def list_alerts():
    """List all health alerts."""
    return jsonify([alert.to_json_dict() for alert in db.find_all_health_alerts()]), 200


@app.route("/alerts/<alert_id>", methods=["GET"])
def get_alert(alert_id: int):
    """Return a single alert by id."""
    health_alert = db.find_health_alert_by_id(alert_id)
    if health_alert is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(health_alert.to_json_dict()), 200


@app.route("/alerts/<int:alert_id>", methods=["PUT"])
def update_alert(alert_id: int):
    """Update an existing alert. Merges payload into stored alert and re-validates."""
    existing = db.find_health_alert_by_id(alert_id)
    if existing is None:
        return jsonify({"error": "Not found"}), 404

    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    payload = request.get_json()
    merged = {**existing.to_json_dict(), **payload}
    try:
        alert = HealthAlertModel.parse_obj(merged)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400

    updated = db.update_health_alert(alert_id, alert)
    return jsonify(updated.to_json_dict()), 200


@app.route("/alerts/<int:alert_id>", methods=["DELETE"])
def delete_alert(alert_id: int):
    """Delete a health alert."""
    if not db.delete_health_alert(alert_id):
        return jsonify({"error": "Not found"}), 404
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
def get_recommendation(profile_id: int):
    """Generate recommendations from recent diary entries using the LLM.

    The LLM returns a complete set of recommendations grouped by symptom/category.
    All existing alerts for the patient are replaced with the new set.

    Optional query parameter: ?model=gemma3:4b
    """
    profile_id = int(profile_id)
    model = request.args.get("model", "gemma3:4b")

    # Fetch entries from DB for this profile, filter to last 30 days
    all_entries = db.find_diary_entries_by_patient_profile_id(profile_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent_entries = []
    for entry in all_entries:
        ts = entry.timestamp
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff:
            recent_entries.append(entry.to_json_dict())

    if not recent_entries:
        return jsonify({"error": "no_recent_entries", "details": "No diary entries in the last 30 days."}), 400

    try:
        recommendations = generate_recommendations(recent_entries, model=model)
    except Exception as exc:
        return jsonify({"error": "llm_error", "details": str(exc)}), 502

    # Replace all existing alerts for this patient with the new set
    db.delete_health_alerts_by_patient_id(profile_id)

    created = []
    for rec in recommendations:
        alert = HealthAlertModel(
            patientProfileId=profile_id,
            title=rec.get("title", "Recommendation"),
            message=rec.get("message", ""),
            timestamp=datetime.utcnow(),
            isRead=False,
            severity=rec.get("severity", 0),
        )
        alert = db.insert_health_alert(alert)
        created.append(alert.to_json_dict())

    return jsonify({"recommendations": created}), 200

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
