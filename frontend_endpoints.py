
from flask import Flask, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError
from typing import Dict

from models import DiaryEntryModel


app = Flask(__name__)
CORS(app)

# Simple in-memory data store (for demo/dev). Keys are entry IDs.
DATA_STORE: Dict[str, dict] = {}


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

    DATA_STORE[entry.id] = entry.to_json_dict()
    return jsonify(DATA_STORE[entry.id]), 201


@app.route("/entries", methods=["GET"])
def list_entries():
    """List all diary entries."""
    return jsonify(list(DATA_STORE.values())), 200


@app.route("/entries/<entry_id>", methods=["GET"])
def get_entry(entry_id: str):
    """Return a single diary entry by id."""
    item = DATA_STORE.get(entry_id)
    if item is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(item), 200


@app.route("/entries/<entry_id>", methods=["PUT"])
def update_entry(entry_id: str):
    """Update an existing diary entry. Merges payload into stored entry and re-validates."""
    if entry_id not in DATA_STORE:
        return jsonify({"error": "Not found"}), 404

    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    payload = request.get_json()
    # Merge existing stored dict with incoming payload (incoming keys override)
    merged = {**DATA_STORE[entry_id], **payload}
    try:
        entry = DiaryEntryModel.parse_obj(merged)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400

    DATA_STORE[entry.id] = entry.to_json_dict()
    return jsonify(DATA_STORE[entry.id]), 200


@app.route("/entries/<entry_id>", methods=["DELETE"])
def delete_entry(entry_id: str):
    """Delete a diary entry."""
    if entry_id not in DATA_STORE:
        return jsonify({"error": "Not found"}), 404
    del DATA_STORE[entry_id]
    return "", 204


if __name__ == "__main__":
    # Useful defaults for local development. In production, run behind a WSGI server.
    app.run(host="0.0.0.0", port=5000, debug=True)
