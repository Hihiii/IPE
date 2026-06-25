from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .constants import ROOT


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML object.")
    return data


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_text(data: str) -> str:
    return digest_bytes(data.encode("utf-8"))


def project_path(value: str | Path) -> Path:
    path = Path(value)
    resolved = path if path.is_absolute() else ROOT / path
    resolved = resolved.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as error:
        raise ValueError(f"Path escapes project root: {value}") from error
    return resolved


def relative_project_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()
