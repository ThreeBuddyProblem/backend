
from flask import Flask, jsonify, request
from flask_cors import CORS
import uuid

app = Flask(__name__)
CORS(app)

# Simple in-memory data store (for demo/dev). Keys are item IDs.
DATA_STORE = {}


@app.route("/health", methods=["GET"])
def health():
	"""Health check endpoint."""
	return jsonify({"status": "ok"}), 200


@app.route("/items", methods=["POST"])
def create_item():
	"""Create a new item. Expects JSON with at least a `name` field.

	Request JSON example:
	{
	  "name": "my item",
	  "metadata": { ... }  # optional
	}
	"""
	if not request.is_json:
		return jsonify({"error": "Expected JSON body"}), 400

	payload = request.get_json()
	name = payload.get("name")
	if not name:
		return jsonify({"error": "Missing required field: name"}), 400

	item_id = str(uuid.uuid4())
	item = {"id": item_id, "name": name, "metadata": payload.get("metadata")}
	DATA_STORE[item_id] = item
	return jsonify(item), 201


@app.route("/items", methods=["GET"])
def list_items():
	"""List all items."""
	return jsonify(list(DATA_STORE.values())), 200


@app.route("/items/<item_id>", methods=["GET"])
def get_item(item_id: str):
	"""Return a single item by id."""
	item = DATA_STORE.get(item_id)
	if item is None:
		return jsonify({"error": "Not found"}), 404
	return jsonify(item), 200


@app.route("/items/<item_id>", methods=["PUT"])
def update_item(item_id: str):
	"""Update an existing item. Accepts JSON and merges fields into the item."""
	if item_id not in DATA_STORE:
		return jsonify({"error": "Not found"}), 404

	if not request.is_json:
		return jsonify({"error": "Expected JSON body"}), 400

	payload = request.get_json()
	# Only merge simple fields; for production consider validation.
	DATA_STORE[item_id].update(payload)
	return jsonify(DATA_STORE[item_id]), 200


@app.route("/items/<item_id>", methods=["DELETE"])
def delete_item(item_id: str):
	"""Delete an item."""
	if item_id not in DATA_STORE:
		return jsonify({"error": "Not found"}), 404
	del DATA_STORE[item_id]
	return "", 204


if __name__ == "__main__":
	# Useful defaults for local development. In production, run behind a WSGI server.
	app.run(host="0.0.0.0", port=5000, debug=True)
