"""Checkpoint read/write/verify for harness phase execution."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

CHECKPOINT_DIR: Path | None = None


def init(checkpoint_dir: str | Path) -> Path:
    global CHECKPOINT_DIR
    CHECKPOINT_DIR = Path(checkpoint_dir)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    return CHECKPOINT_DIR


def _dir() -> Path:
    assert CHECKPOINT_DIR is not None, "harness_checkpoint.init() not called"
    return CHECKPOINT_DIR


def phase_key(phase_id: str) -> str:
    return f"checkpoint_{phase_id}"


def status_file() -> Path:
    return _dir() / "_status.json"


def read_status() -> dict:
    sf = status_file()
    if sf.exists():
        return json.loads(sf.read_text(encoding="utf-8"))
    return {"current_phase": None, "completed_phases": [], "error": None}


def write_status(**kwargs) -> None:
    data = read_status()
    data.update(kwargs)
    data["_updated_at"] = time.time()
    status_file().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_failure_trace(packet: dict, error: Exception) -> Path:
    """Persist a bounded failure receipt beside the resumable session."""
    path = _dir() / "failure_trace.json"
    payload = {
        "packet_id": packet.get("packet_id"),
        "packet_hash": packet.get("packet_hash"),
        "error": str(error),
        "failures": getattr(error, "failures", []),
        "generated_at": time.time(),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_execution_record(record: dict) -> Path:
    path = _dir() / "execution_record.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write(phase_id: str, phase_data: dict, /, *, content_hash: str | None = None) -> Path:
    key = phase_key(phase_id)
    path = _dir() / f"{key}.json"
    payload = {
        "phase_id": phase_id,
        "timestamp": time.time(),
        "content_hash": content_hash or _hash(phase_data),
        "data": phase_data,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    completed = read_status().get("completed_phases", [])
    if phase_id not in completed:
        completed.append(phase_id)
    write_status(current_phase=phase_id, completed_phases=completed, error=None)
    return path


def write_request(request: str) -> Path:
    """Persist session input without treating it as a completed pipeline phase."""
    path = _dir() / "request.json"
    path.write_text(json.dumps({"request": request, "timestamp": time.time()}, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def read_request() -> str:
    path = _dir() / "request.json"
    if not path.exists():
        return ""
    return str(json.loads(path.read_text(encoding="utf-8")).get("request", ""))


def write_prompt(phase_id: str, prompt_payload: dict) -> Path:
    path = _dir() / f"prompt_{phase_id}.json"
    path.write_text(json.dumps(prompt_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_status(current_phase=phase_id, waiting_for_input=True, error=None)
    return path


def write_response(phase_id: str, response_data: dict) -> Path:
    path = _dir() / f"response_{phase_id}.json"
    path.write_text(json.dumps(response_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def read_response(phase_id: str) -> dict | None:
    path = _dir() / f"response_{phase_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def clear_response(phase_id: str) -> None:
    path = _dir() / f"response_{phase_id}.json"
    if path.exists():
        path.unlink()


def read(phase_id: str) -> dict | None:
    key = phase_key(phase_id)
    path = _dir() / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def verify(phase_id: str, expected_hash: str | None = None) -> bool:
    cp = read(phase_id)
    if cp is None:
        return False
    if expected_hash is not None:
        return cp.get("content_hash") == expected_hash
    content_hash = _hash(cp.get("data", {}))
    return cp.get("content_hash") == content_hash


def verify_chain(phase_ids: list[str]) -> list[str]:
    """Return list of missing phase ids in the checkpoint chain."""
    missing = []
    for pid in phase_ids:
        cp = read(pid)
        if cp is None:
            missing.append(pid)
        elif not verify(pid):
            missing.append(f"{pid}(tampered)")
    return missing


def _hash(data: dict) -> str:
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def clean() -> None:
    """Remove all checkpoints and status for a fresh start."""
    d = _dir()
    for f in d.glob("checkpoint_*.json"):
        f.unlink()
    for f in d.glob("prompt_*.json"):
        f.unlink()
    for f in d.glob("response_*.json"):
        f.unlink()
    request = d / "request.json"
    if request.exists():
        request.unlink()
    sf = status_file()
    if sf.exists():
        sf.unlink()
