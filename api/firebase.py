import os
import json
import firebase_admin
from firebase_admin import credentials, initialize_app
from http.server import BaseHTTPRequestHandler

# ✅ Optional: load from .env file for local testing
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required on Vercel

# ✅ Load service account from env
google_creds = os.environ.get("GOOGLE_CREDENTIALS")

if not google_creds:
    raise ValueError("GOOGLE_CREDENTIALS is not set!")

# ✅ Determine if it's a file path or a JSON string
if google_creds.strip().endswith(".json"):
    if not os.path.exists(google_creds):
        raise FileNotFoundError(f"Service account file not found: {google_creds}")
    with open(google_creds, "r") as f:
        creds_dict = json.load(f)
else:
    try:
        creds_dict = json.loads(google_creds)
    except json.JSONDecodeError as e:
        print("❌ Failed to parse GOOGLE_CREDENTIALS as JSON.")
        raise e

# ✅ Initialize Firebase Admin (only once)
if not firebase_admin._apps:
    cred = credentials.Certificate(creds_dict)
    initialize_app(cred)

# ✅ Vercel-compatible HTTP handler
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("✅ Firebase initialized successfully!".encode("utf-8"))
