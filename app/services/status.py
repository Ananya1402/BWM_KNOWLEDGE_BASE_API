# services/status.py
import threading
from typing import Dict

_lock = threading.Lock()
_STATUS_STORE: Dict[str, str] = {}


def set_status(job_id: str, status: str) -> None:
    with _lock:
        _STATUS_STORE[job_id] = status


def get_status(job_id: str) -> str:
    with _lock:
        return _STATUS_STORE.get(job_id, "unknown")
