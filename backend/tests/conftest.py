"""Test setup: isolated data folder, no auto-seed, no real credentials."""

import os
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="claimpilot-test-")
os.environ["AUTO_SEED"] = "false"
# Empty values stop python-dotenv from loading real keys from a local .env file.
os.environ["GOOGLE_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
