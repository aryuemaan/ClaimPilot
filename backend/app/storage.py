"""Persistence: documents (claims, policies, past claims) and binary files.

Local development uses JSON files and a folder on disk. On Cloud Run set
STORE_BACKEND=firestore and GCS_BUCKET=<bucket> to use Firestore + Cloud Storage.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from pathlib import Path
from typing import Any

from .config import settings

log = logging.getLogger("claimpilot.storage")


# ---------------------------------------------------------------------------
# Document store
# ---------------------------------------------------------------------------


class LocalDocStore:
    kind = "local-json"

    def __init__(self, root: Path) -> None:
        self.root = root / "db"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, coll: str, doc_id: str) -> Path:
        safe = "".join(c for c in doc_id if c.isalnum() or c in "-_.")
        return self.root / coll / f"{safe}.json"

    async def get(self, coll: str, doc_id: str) -> dict | None:
        p = self._path(coll, doc_id)
        if not p.exists():
            return None
        with self._lock:
            return json.loads(p.read_text("utf-8"))

    async def put(self, coll: str, doc_id: str, doc: dict) -> None:
        p = self._path(coll, doc_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        with self._lock:
            tmp.write_text(json.dumps(doc, ensure_ascii=False, default=str), "utf-8")
            tmp.replace(p)

    async def update(self, coll: str, doc_id: str, patch: dict) -> dict:
        with self._lock:
            p = self._path(coll, doc_id)
            doc = json.loads(p.read_text("utf-8")) if p.exists() else {}
            doc.update(patch)
            tmp = p.with_suffix(".tmp")
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(doc, ensure_ascii=False, default=str), "utf-8")
            tmp.replace(p)
            return doc

    async def list(self, coll: str) -> list[dict]:
        d = self.root / coll
        if not d.exists():
            return []
        with self._lock:
            return [json.loads(p.read_text("utf-8")) for p in d.glob("*.json")]

    async def clear(self, coll: str) -> None:
        d = self.root / coll
        if d.exists():
            with self._lock:
                for p in d.glob("*.json"):
                    p.unlink()


class FirestoreDocStore:
    kind = "firestore"

    def __init__(self) -> None:
        from google.cloud import firestore  # imported lazily

        self.db = firestore.Client(project=settings.project or None, database=settings.firestore_database)

    async def get(self, coll: str, doc_id: str) -> dict | None:
        snap = await asyncio.to_thread(self.db.collection(coll).document(doc_id).get)
        return snap.to_dict() if snap.exists else None

    async def put(self, coll: str, doc_id: str, doc: dict) -> None:
        clean = json.loads(json.dumps(doc, default=str))
        await asyncio.to_thread(self.db.collection(coll).document(doc_id).set, clean)

    async def update(self, coll: str, doc_id: str, patch: dict) -> dict:
        clean = json.loads(json.dumps(patch, default=str))
        ref = self.db.collection(coll).document(doc_id)
        await asyncio.to_thread(ref.set, clean, merge=True)
        snap = await asyncio.to_thread(ref.get)
        return snap.to_dict() or {}

    async def list(self, coll: str) -> list[dict]:
        docs = await asyncio.to_thread(lambda: list(self.db.collection(coll).stream()))
        return [d.to_dict() for d in docs]

    async def clear(self, coll: str) -> None:
        def _clear():
            for d in self.db.collection(coll).stream():
                d.reference.delete()
        await asyncio.to_thread(_clear)


# ---------------------------------------------------------------------------
# File store
# ---------------------------------------------------------------------------


class LocalFileStore:
    kind = "local-disk"

    def __init__(self, root: Path) -> None:
        self.root = root / "files"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError("invalid key")
        return p

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        p.with_name(p.name + ".type").write_text(content_type)

    async def load(self, key: str) -> tuple[bytes, str] | None:
        p = self._path(key)
        if not p.exists():
            return None
        ctype_file = p.with_name(p.name + ".type")
        ctype = ctype_file.read_text() if ctype_file.exists() else "application/octet-stream"
        return p.read_bytes(), ctype

    async def delete_prefix(self, prefix: str) -> None:
        import shutil

        p = self._path(prefix)
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


class GcsFileStore:
    kind = "cloud-storage"

    def __init__(self, bucket: str) -> None:
        from google.cloud import storage

        self.bucket = storage.Client(project=settings.project or None).bucket(bucket)

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        blob = self.bucket.blob(key)
        await asyncio.to_thread(blob.upload_from_string, data, content_type=content_type)

    async def load(self, key: str) -> tuple[bytes, str] | None:
        blob = self.bucket.blob(key)
        try:
            data = await asyncio.to_thread(blob.download_as_bytes)
        except Exception:
            return None
        return data, blob.content_type or "application/octet-stream"

    async def delete_prefix(self, prefix: str) -> None:
        def _del():
            for b in self.bucket.list_blobs(prefix=prefix):
                b.delete()
        await asyncio.to_thread(_del)


def _make_doc_store():
    if settings.store_backend == "firestore":
        try:
            return FirestoreDocStore()
        except Exception as exc:
            log.error("Firestore unavailable (%s) - falling back to local JSON store", exc)
    return LocalDocStore(settings.data_dir)


def _make_file_store():
    if settings.gcs_bucket:
        try:
            return GcsFileStore(settings.gcs_bucket)
        except Exception as exc:
            log.error("Cloud Storage unavailable (%s) - falling back to local disk", exc)
    return LocalFileStore(settings.data_dir)


docs = _make_doc_store()
files = _make_file_store()


def describe() -> dict[str, Any]:
    return {"documents": docs.kind, "files": files.kind}
