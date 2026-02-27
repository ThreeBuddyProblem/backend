
from flask import Flask, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError
from typing import Dict

from models import DiaryEntryModel, PatientProfileModel, HealthAlertModel


app = Flask(__name__)
CORS(app)

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


@app.route("/entries", methods=["GET"])
def list_entries():
    """List all diary entries."""
    return jsonify(list(DIARY_STORE.values())), 200


@app.route("/entries/<entry_id>", methods=["GET"])
def get_entry(entry_id: str):
    """Return a single diary entry by id."""
    item = DIARY_STORE.get(entry_id)
    if item is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(item), 200


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
    return jsonify(list(PROFILE_STORE.values())), 200


@app.route("/profiles/<profile_id>", methods=["GET"])
def get_profile(profile_id: str):
    """Return a single profile by id."""
    item = PROFILE_STORE.get(profile_id)
    if item is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(item), 200


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
    return jsonify(list(ALERT_STORE.values())), 200


@app.route("/alerts/<alert_id>", methods=["GET"])
def get_alert(alert_id: str):
    """Return a single alert by id."""
    item = ALERT_STORE.get(alert_id)
    if item is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(item), 200


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


if __name__ == "__main__":
    # Useful defaults for local development. In production, run behind a WSGI server.
    app.run(host="0.0.0.0", port=5000, debug=True)
