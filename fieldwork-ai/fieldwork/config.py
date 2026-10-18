"""Settings read from the environment. Model names live here only, never in feature code."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("FW_DATA_DIR", ROOT / "data"))
STORE_DIR = Path(os.getenv("FW_STORE_DIR", ROOT / "store"))
LOG_DIR = Path(os.getenv("FW_LOG_DIR", ROOT / "logs"))

# Gemini models (override with env vars when Google renames or retires a model).
MODEL_FLASH = os.getenv("FW_MODEL_FLASH", "gemini-3.8-flash")
MODEL_LITE = os.getenv("FW_MODEL_LITE", "gemini-3.5-flash-lite")
DINO_MODEL = "facebook/dinov2-small"
# Provisional candidate filter, not a calibrated decision threshold.
CHANGE_SCORE = float(os.getenv("FW_CHANGE_SCORE", "3.5"))
# Tried in order when a model is overloaded (503) or over quota (429).
MODEL_FALLBACKS = os.getenv("FW_MODEL_FALLBACKS", "gemini-3.7-flash,gemini-3.5-flash").split(",")

# Cloud deployment: Vertex AI (Application Default Credentials) instead of an API key; Firestore + GCS instead of files.
USE_VERTEX = os.getenv("FW_USE_VERTEX", "0") == "1"
GCP_PROJECT = os.getenv("FW_GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = os.getenv("FW_GCP_LOCATION", "global")
# ADK creates its own GenAI client; give it the same Vertex configuration.
if USE_VERTEX:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    if GCP_PROJECT:
        os.environ["GOOGLE_CLOUD_PROJECT"] = GCP_PROJECT
    os.environ["GOOGLE_CLOUD_LOCATION"] = GCP_LOCATION
STORE_KIND = os.getenv("FW_STORE", "local")  # local | cloud
BUCKET = os.getenv("FW_BUCKET", "")
WORK_DIR = Path(os.getenv("FW_WORK_DIR", "/tmp/fieldwork"))  # CloudStore's local scratch space

# New Windows user variables only reach freshly started programs; fall back to the registry.
if not os.getenv("GEMINI_API_KEY") and os.name == "nt":
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as _k:
            os.environ["GEMINI_API_KEY"] = winreg.QueryValueEx(_k, "GEMINI_API_KEY")[0]
    except OSError:
        pass

# Use the corporate/system certificate store for all outbound HTTPS.
USE_SYSTEM_CERTS = os.getenv("FW_SYSTEM_CERTS", "1") == "1"

for _d in (DATA_DIR, LOG_DIR) + ((STORE_DIR,) if STORE_KIND == "local" else ()):
    _d.mkdir(parents=True, exist_ok=True)
