import json
import threading
from datetime import datetime
from pathlib import Path

_HEALTH_FILE = Path("storage/health.json")
_LOCK = threading.Lock()


class HealthRecorder:
    def __init__(self):
        self.state = {}
        self._load()

    def _load(self):
        if _HEALTH_FILE.exists():
            self.state = json.loads(_HEALTH_FILE.read_text())
        else:
            self.state = {
                "service_started_at": self._now(),
                "last_error": None,
                "total_invoices_seen": 0,
                "total_invoices_new": 0,
                "total_detail_success": 0,
                "total_detail_failed": 0,
            }
            self._save()

    def _save(self):
        with _LOCK:
            _HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
            _HEALTH_FILE.write_text(
                json.dumps(self.state, indent=2, ensure_ascii=False)
            )

    @staticmethod
    def _now():
        return datetime.utcnow().isoformat()

    # -------- recorders --------

    def mark(self, key: str):
        self.state[key] = self._now()
        self._save()

    def inc(self, key: str, delta: int = 1):
        self.state[key] = self.state.get(key, 0) + delta
        self._save()

    def error(self, message: str):
        self.state["last_error"] = {
            "time": self._now(),
            "message": message,
        }
        self._save()
