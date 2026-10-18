"""Where records, cases and media live. LocalStore (files) for development; a
CloudStore (Firestore + Cloud Storage, same methods) replaces it on deploy; pick with FW_STORE=local|cloud."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from . import config


class LocalStore:
    def __init__(self, root: Path = config.STORE_DIR):
        self.root = root

    def item_dir(self, item_id: str) -> Path:
        d = self.root / "items" / item_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def put_json(self, kind: str, key: str, data: dict) -> None:
        d = self.root / kind
        d.mkdir(parents=True, exist_ok=True)
        # Queue readers must never see a partially written evidence report.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=d, suffix=".tmp", delete=False) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            tmp = Path(f.name)
        tmp.replace(d / f"{key}.json")

    def get_json(self, kind: str, key: str) -> dict | None:
        p = self.root / kind / f"{key}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def list_json(self, kind: str) -> list[dict]:
        d = self.root / kind
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob("*.json"))] if d.exists() else []

    def put_file(self, item_id: str, src: Path, name: str | None = None) -> Path:
        dst = self.item_dir(item_id) / (name or src.name)
        if src.resolve() != dst.resolve():
            shutil.copyfile(src, dst)
        return dst

    def get_file(self, item_id: str, name: str) -> Path | None:
        """Local path of items/<item_id>/<name>, or None. Refuses paths outside the item folder."""
        base = (self.root / "items" / item_id).resolve()
        p = (base / name).resolve()
        return p if base in p.parents and p.is_file() else None

    def sync_item(self, item_id: str) -> None:
        """No-op locally; CloudStore uploads new files here."""

    def media_url(self, item_id: str, name: str) -> str:
        return f"/media/{item_id}/{name}"


class CloudStore(LocalStore):
    """Records in Firestore (collection = kind, doc id = key), files in GCS (items/<id>/<name>).
    Pipelines still write to a local working dir; call sync_item(item_id) to upload it."""

    def __init__(self, bucket: str = config.BUCKET, work_dir: Path = config.WORK_DIR, project: str | None = config.GCP_PROJECT):
        from google.cloud import firestore, storage

        super().__init__(Path(work_dir))
        self.db = firestore.Client(project=project)
        self.bucket = storage.Client(project=project).bucket(bucket)
        self._synced: dict[str, set[tuple[str, int]]] = {}

    def put_json(self, kind: str, key: str, data: dict) -> None:
        self.db.collection(kind).document(key).set(json.loads(json.dumps(data, ensure_ascii=False)))

    def get_json(self, kind: str, key: str) -> dict | None:
        snap = self.db.collection(kind).document(key).get()
        return snap.to_dict() if snap.exists else None

    def list_json(self, kind: str) -> list[dict]:
        return [d.to_dict() for d in self.db.collection(kind).stream()]

    def sync_item(self, item_id: str) -> None:
        """Upload files in the item's working dir that are new or changed since the last sync."""
        base = self.item_dir(item_id)
        done = self._synced.setdefault(item_id, set())
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(base).as_posix()
            sig = (rel, p.stat().st_size)
            if sig not in done:
                self.bucket.blob(f"items/{item_id}/{rel}").upload_from_filename(str(p))
                done.add(sig)

    def get_file(self, item_id: str, name: str) -> Path | None:
        p = super().get_file(item_id, name)
        if p is not None:
            return p
        base = (self.root / "items" / item_id).resolve()
        dst = (base / name).resolve()
        if base not in dst.parents:
            return None
        blob = self.bucket.blob(f"items/{item_id}/{name}")
        if not blob.exists():
            return None
        dst.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dst))
        return dst


def make_store() -> LocalStore:
    return CloudStore() if config.STORE_KIND == "cloud" else LocalStore()


store = make_store()
