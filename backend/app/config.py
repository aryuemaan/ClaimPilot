"""Runtime configuration, read once from environment variables.

Everything has a sensible default so `uvicorn app.main:app` works out of the box.
See `.env.example` at the repo root for the full list.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the repo root (one level above backend/) and from backend/.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_DIR = _BACKEND_DIR.parent
load_dotenv(_REPO_DIR / ".env")
load_dotenv(_BACKEND_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        # --- Models -----------------------------------------------------------
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        # Optional heavier model for the final adjudication step.
        self.adjudicator_model: str = os.getenv("ADJUDICATOR_MODEL", self.gemini_model)
        self.gemma_model: str = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")
        # "low" keeps the pipeline fast. Set to "" for models that don't
        # support thinking levels (e.g. gemini-2.5-*).
        self.thinking_level: str = os.getenv("THINKING_LEVEL", "low").strip().lower()

        # --- Credentials --------------------------------------------------------
        self.api_key: str = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
        if self.api_key and not os.getenv("GOOGLE_API_KEY"):
            # ADK / google-genai read GOOGLE_API_KEY.
            os.environ["GOOGLE_API_KEY"] = self.api_key
        # Vertex AI ("enterprise") mode uses the Cloud Run service account instead of an API key.
        # GOOGLE_GENAI_USE_ENTERPRISE is the current name; GOOGLE_GENAI_USE_VERTEXAI still works.
        self.use_vertex: bool = _bool("GOOGLE_GENAI_USE_ENTERPRISE") or _bool("GOOGLE_GENAI_USE_VERTEXAI")
        self.project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        self.location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
        if self.use_vertex:
            os.environ.setdefault("GOOGLE_CLOUD_LOCATION", self.location)

        # Offline demo mode: the full ADK pipeline runs, but a scripted model
        # stands in for Gemini. Used automatically when no credentials exist.
        self.offline: bool = _bool("FORCE_OFFLINE") or not (self.api_key or self.use_vertex)

        # --- Storage ------------------------------------------------------------
        self.store_backend: str = os.getenv("STORE_BACKEND", "local").lower()  # local | firestore
        self.firestore_database: str = os.getenv("FIRESTORE_DATABASE", "(default)")
        self.gcs_bucket: str = os.getenv("GCS_BUCKET", "")
        self.data_dir: Path = Path(os.getenv("DATA_DIR", str(_BACKEND_DIR / "data"))).resolve()

        # --- Paths --------------------------------------------------------------
        self.repo_dir: Path = _REPO_DIR
        self.sample_photos_dir: Path = Path(
            os.getenv("SAMPLE_PHOTOS_DIR", str(_REPO_DIR / "sample-data" / "photos"))
        ).resolve()
        self.frontend_dist: Path = Path(
            os.getenv("FRONTEND_DIST", str(_REPO_DIR / "frontend" / "dist"))
        ).resolve()

        # --- Behaviour ----------------------------------------------------------
        self.auto_seed: bool = _bool("AUTO_SEED", True)
        self.pipeline_timeout: int = int(os.getenv("PIPELINE_TIMEOUT_SECONDS", "300"))
        self.app_version: str = "1.0.0"

    @property
    def gemma_enabled(self) -> bool:
        # Gemma is served through the Gemini API (API key), not Vertex generateContent.
        return bool(self.api_key) and not self.offline and bool(self.gemma_model)

    @property
    def mode(self) -> str:
        return "offline" if self.offline else "live"

    @property
    def backend_label(self) -> str:
        if self.offline:
            return "Offline demo model"
        return "Vertex AI" if self.use_vertex else "Gemini API"


settings = Settings()
