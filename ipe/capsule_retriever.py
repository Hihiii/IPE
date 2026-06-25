from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .io import digest_bytes, digest_text, load_yaml, project_path, relative_project_path
from .module_router import load_module_map, validate_module_map


def load_capsules(module_plan: dict[str, Any]) -> dict[str, Any]:
    capsules = []
    access_log = []
    for module in module_plan["modules"]:
        path = project_path(module["capsule_path"])
        raw = path.read_bytes()
        capsule = load_yaml(path)
        capsules.append(capsule)
        access_log.append(
            {
                "module_id": module["id"],
                "kind": "capsule",
                "path": relative_project_path(path),
                "source_hash": digest_bytes(raw),
                "line_count": path.read_text(encoding="utf-8").count("\n") + 1,
            }
        )
    return {"capsules": capsules, "access_log": access_log}


def capsule_plan(module_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "capsules": [
            {
                "module_id": module["id"],
                "capsule_path": module["capsule_path"],
                "full_yaml_paths": module.get("full_yaml_paths", []),
                "materialize_full_yaml": False,
            }
            for module in module_plan["modules"]
        ],
    }


def materialize_phase(module_plan: dict[str, Any], phase_id: str) -> dict[str, Any]:
    sources = []
    access_log = []
    for module in module_plan["modules"]:
        if phase_id not in module["phases"]:
            continue
        for source_path in module.get("full_yaml_paths", []):
            path = project_path(source_path)
            raw = path.read_bytes()
            text = path.read_text(encoding="utf-8")
            sources.append(
                {
                    "module_id": module["id"],
                    "path": relative_project_path(path),
                    "content_yaml": text,
                    "source_hash": digest_bytes(raw),
                    "context_hash": digest_text(text),
                }
            )
            access_log.append(
                {
                    "module_id": module["id"],
                    "kind": "full_yaml",
                    "phase_id": phase_id,
                    "path": relative_project_path(path),
                    "source_hash": digest_bytes(raw),
                    "line_count": text.count("\n") + 1,
                }
            )
    return {"phase_id": phase_id, "sources": sources, "access_log": access_log}


def validate_capsules() -> dict[str, Any]:
    module_map = load_module_map()
    validate_module_map(module_map)
    errors = []
    for module in module_map["modules"]:
        path = project_path(module["capsule_path"])
        capsule = load_yaml(path)
        if capsule.get("module_id") != module["id"]:
            errors.append({"module_id": module["id"], "path": module["capsule_path"], "error": "module_id mismatch"})
    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True, "module_count": len(module_map["modules"])}


def build_capsules(overwrite: bool = False) -> dict[str, Any]:
    module_map = load_module_map()
    written = []
    for module in module_map["modules"]:
        path = project_path(module["capsule_path"])
        if path.exists() and not overwrite:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": "1.0.0",
            "module_id": module["id"],
            "summary": f"Generated compact capsule for {module['system']}.",
            "phase_focus": module["phases"],
            "claims": module["claims"],
        }
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        written.append(relative_project_path(path))
    return {"written": written, "module_count": len(module_map["modules"])}
