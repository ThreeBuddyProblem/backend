from __future__ import annotations

import argparse
import logging
import tempfile
from typing import Optional

from flask import Flask, jsonify, request


def create_app(model_name: str = "openai/whisper-small", device: Optional[str] = None):
	app = Flask(__name__)

	import torch
	import torchaudio
	from transformers import WhisperProcessor, WhisperForConditionalGeneration

	# Choose device
	if device is None:
		if torch.cuda.is_available():
			_device = "cuda"
		elif torch.backends.mps.is_available():
			_device = "mps"
		else:
			_device = "cpu"
	else:
		_device = device

	logging.info("Loading Whisper model %s on %s", model_name, _device)
	processor = WhisperProcessor.from_pretrained(model_name)
	model = WhisperForConditionalGeneration.from_pretrained(model_name).to(_device)
	model.eval()

	@app.route("/transcribe", methods=["POST"])
	def transcribe():
		if "file" not in request.files:
			return jsonify({"error": "missing_file"}), 400

		f = request.files["file"]
		# save to temp file for torchaudio to read
		with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
			f.save(tmp.name)
			tmp_path = tmp.name

		try:
			waveform, sr = torchaudio.load(tmp_path)
			# resample to 16000
			if sr != 16000:
				resampler = torchaudio.transforms.Resample(sr, 16000)
				waveform = resampler(waveform)
			if waveform.shape[0] > 1:
				waveform = waveform.mean(dim=0, keepdim=True)

			audio = waveform.squeeze().numpy().astype("float32")

			inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
			input_features = inputs.input_features.to(_device)

			with torch.no_grad():
				predicted_ids = model.generate(
					input_features,
					max_new_tokens=256,
                    language=request.form.get("language"),
				)

			text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()
			return jsonify({"text": text}), 200
		except Exception as exc:
			logging.exception("Transcription failed: %s", exc)
			return jsonify({"error": "transcription_failed", "details": str(exc)}), 500
		finally:
			try:
				tmp.close()
			except Exception:
				pass

	return app


def parse_args():
	p = argparse.ArgumentParser()
	p.add_argument("--model", default="openai/whisper-small")
	p.add_argument("--host", default="0.0.0.0")
	p.add_argument("--port", type=int, default=11435)
	p.add_argument("--device", default=None)
	return p.parse_args()


if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO)
	args = parse_args()
	app = create_app(model_name=args.model, device=args.device)
	app.run(host=args.host, port=args.port)

