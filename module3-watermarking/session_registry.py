import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import config


class SessionRegistry:
    """
    JSON-backed registry of watermarking sessions.

    Each session entry:
    {
        "session_id_hex": "a1b2c3d4e5f6a7b8",
        "session_id_int": 11671527838978859960,
        "viewer_name": "Viewer B - ESPN US",
        "account_id": "user_9283@espn.com",
        "region": "United States",
        "platform": "Smart TV",
        "ip_address": "192.168.x.x",
        "timestamp": "2024-03-15T20:47:13Z",
        "source_video": "normalized_source_01.mp4",
        "watermarked_file": "watermarked_outputs/viewerB_source01.mp4",
        "layers_embedded": ["layer1", "layer2", "layer3"],
        "module1_fingerprint": null
    }
    """

    def __init__(self):
        self.sessions: dict = {}  # session_id_hex -> entry
        self._load()

    def create_session(self,
                       viewer_name: str,
                       source_video: str,
                       account_id: str = "",
                       region: str = "",
                       platform: str = "",
                       ip_address: str = "") -> dict:
        hex_str = uuid.uuid4().hex[:16]
        session_id_int = int(hex_str, 16)
        entry = {
            "session_id_hex": hex_str,
            "session_id_int": session_id_int,
            "viewer_name": viewer_name,
            "account_id": account_id,
            "region": region,
            "platform": platform,
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_video": source_video,
            "watermarked_file": None,
            "layers_embedded": [],
            "module1_fingerprint": None,
        }
        self.sessions[hex_str] = entry
        self._save()
        return entry

    def lookup_by_int(self, session_id_int: int):
        hex_str = format(session_id_int, '016x')
        return self.sessions.get(hex_str)

    def lookup_by_hex(self, session_id_hex: str):
        return self.sessions.get(session_id_hex)

    def update_watermarked_file(self, session_id_hex: str,
                                 filepath: str,
                                 layers: list) -> None:
        if session_id_hex in self.sessions:
            self.sessions[session_id_hex]["watermarked_file"] = filepath
            self.sessions[session_id_hex]["layers_embedded"] = layers
            self._save()

    def list_sessions(self) -> list:
        return sorted(
            self.sessions.values(),
            key=lambda e: e["timestamp"],
            reverse=True
        )

    def _save(self):
        temp = Path(config.REGISTRY_PATH + ".tmp")
        data = list(self.sessions.values())
        temp.write_text(json.dumps(data, indent=2, default=str))
        temp.replace(config.REGISTRY_PATH)

    def _load(self):
        path = Path(config.REGISTRY_PATH)
        if not path.exists():
            return
        data = json.loads(path.read_text())
        self.sessions = {e["session_id_hex"]: e for e in data}

    def reset(self):
        self.sessions = {}
        path = Path(config.REGISTRY_PATH)
        if path.exists():
            path.unlink()
