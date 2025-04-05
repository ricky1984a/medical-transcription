"""
Run script for Medical Transcription App
"""

import os
import logging
import json
import firebase_admin
from firebase_admin import credentials

# ✅ Optional: load .env for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Don't crash if dotenv is not available

# ✅ Try to clear SQLAlchemy mappers before loading models
try:
    from sqlalchemy.orm import clear_mappers
    clear_mappers()
    print("SQLAlchemy mappers cleared")
except ImportError:
    print("Could not import clear_mappers from sqlalchemy.orm")
    pass

# ✅ Firebase Admin SDK Initialization
google_creds = os.environ.get("GOOGLE_CREDENTIALS")
if not google_creds:
    raise ValueError("Missing GOOGLE_CREDENTIALS environment variable.")

try:
    # Determine if GOOGLE_CREDENTIALS is a path or JSON string
    if google_creds.strip().endswith(".json") and os.path.exists(google_creds):
        with open(google_creds, "r") as f:
            creds_dict = json.load(f)
    else:
        creds_dict = json.loads(google_creds)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(creds_dict))
        print("✅ Firebase Admin initialized")

except Exception as e:
    print("❌ Failed to initialize Firebase Admin:", e)
    raise e

# ✅ Import and create the Flask app
from api.__init__ import create_app
from api.config import config

app = create_app()

@app.route("/api/", methods=["GET"])
def home():
    from flask import jsonify
    return jsonify({
        "message": "Medical Transcription API",
        "status": "running"
    })

@app.route("/api/health", methods=["GET"])
def health():
    from flask import jsonify
    return jsonify({
        "status": "healthy"
    })

if __name__ == "__main__":
    # Get port and debug from env or config
    port = int(os.environ.get("PORT", config.get_port()))
    debug = os.environ.get("DEBUG", config.get_debug())
    if isinstance(debug, str):
        debug = debug.lower() in ('true', '1', 't', 'y', 'yes')

    # Run the Flask app
    app.run(host="0.0.0.0", port=port, debug=debug)
