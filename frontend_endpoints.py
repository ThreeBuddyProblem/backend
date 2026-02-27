
from flask import Flask, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError
from typing import Dict
from datetime import datetime, timedelta
import os
import tempfile

from models import DiaryEntryModel, PatientProfileModel, HealthAlertModel
from llm_dispatcher import generate_recommendation_from_entries


app = Flask(__name__)
CORS(app)

# --- Whisper model loading (lazy, on first transcribe request) ---
_whisper_model = None
_whisper_processor = None
_whisper_device = None


def _load_whisper():
    global _whisper_model, _whisper_processor, _whisper_device
    if _whisper_model is not None:
        return

    import torch
    from transformers import WhisperProcessor, WhisperForConditionalGeneration

    MODEL_NAME = "openai/whisper-small"
    _whisper_device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Loading Whisper model: {MODEL_NAME} ({_whisper_device})...")
    _whisper_processor = WhisperProcessor.from_pretrained(MODEL_NAME)
    _whisper_model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME).to(_whisper_device)
    _whisper_model.eval()
    print("Whisper model ready!")

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


## Transcription endpoint ################################

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    """Transcribe an uploaded audio file using Whisper.

    Accepts multipart form data with:
      - file: audio file (WAV, m4a, etc.)
      - language: language code (e.g. 'hu', 'en') — optional, defaults to 'hu'

    Returns: {"text": "transcribed text..."}
    """
    import torch
    import torchaudio
    import numpy as np

    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["file"]
    language = request.form.get("language", "hu")

    # Save uploaded file to a temp location
    suffix = os.path.splitext(audio_file.filename or "audio.m4a")[1] or ".m4a"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        audio_file.save(tmp)
        tmp_path = tmp.name

    try:
        _load_whisper()

        # Load and resample audio to 16kHz mono float32
        waveform, sample_rate = torchaudio.load(tmp_path)
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        audio_np = waveform.squeeze().numpy().astype(np.float32)

        # Run Whisper inference
        inputs = _whisper_processor(
            audio_np,
            sampling_rate=16000,
            return_tensors="pt",
        )
        input_features = inputs.input_features.to(_whisper_device)

        with torch.no_grad():
            predicted_ids = _whisper_model.generate(
                input_features,
                language=language,
                task="transcribe",
                max_new_tokens=256,
            )

        text = _whisper_processor.batch_decode(
            predicted_ids, skip_special_tokens=True
        )[0].strip()

        return jsonify({"text": text}), 200

    except Exception as exc:
        return jsonify({"error": "transcription_failed", "details": str(exc)}), 500
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    # Useful defaults for local development. In production, run behind a WSGI server.
    app.run(host="0.0.0.0", port=5001, debug=True)


@app.route("/recommendation", methods=["GET"])
def get_recommendation():
    """Generate a recommendation from all diary entries using the LLM.

    Optional query parameter: ?model=gemma3:4b
    Returns the raw JSON returned by the LLM endpoint under the `recommendation` key.
    """
    model = request.args.get("model", "gemma3:4b")
    try:
        # Only use entries from the last 30 days
        cutoff = datetime.utcnow() - timedelta(days=30)
        recent_entries = []
        for e in DIARY_STORE.values():
            ts = e.get("timestamp")
            if not ts:
                continue
            # Accept ISO timestamps with or without trailing 'Z'
            try:
                if isinstance(ts, str) and ts.endswith("Z"):
                    parsed = datetime.fromisoformat(ts[:-1])
                else:
                    parsed = datetime.fromisoformat(ts)
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

    return jsonify({"recommendation": llm_response}), 200

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backend server")
    parser.add_argument("--port", required=False, help="Port of the server", default=5000)
    return parser.parse_args()

if __name__ == "__main__":
    # Useful defaults for local development. In production, run behind a WSGI server.
    args = parse_args()
    app.run(host="0.0.0.0", port=args.port, debug=True)
