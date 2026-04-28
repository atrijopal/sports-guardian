# storage.py — JSON-backed fingerprint database. Dumb by design.

import json
from pathlib import Path
import config

_DB_PATH = Path(config.DB_PATH)


def load_db() -> list[dict]:
    """Read JSON file, return empty list if missing or corrupt."""
    if not _DB_PATH.exists():
        return []
    try:
        return json.loads(_DB_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_db(db: list[dict]) -> None:
    """Write full DB list to JSON file."""
    _DB_PATH.write_text(json.dumps(db, indent=2), encoding="utf-8")


def add_fingerprint(entry: dict) -> None:
    """Append a fingerprint entry and persist."""
    db = load_db()
    db.append(entry)
    save_db(db)


def list_fingerprints() -> list[dict]:
    """Return metadata only (no hashes) for UI display."""
    db = load_db()
    return [
        {
            "video_id": e["video_id"],
            "name": e["name"],
            "registered_at": e["registered_at"],
            "duration_sec": e.get("duration_sec"),
        }
        for e in db
    ]


def get_all_fingerprints() -> list[dict]:
    """Return full entries including all layer fingerprint data."""
    return load_db()
