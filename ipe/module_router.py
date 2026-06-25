from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .constants import MASTER_MODULE_MAP, PHASES
from .io import load_yaml, project_path


class ModuleMapError(ValueError):
    pass


def load_module_map(path: Path = MASTER_MODULE_MAP) -> dict[str, Any]:
    module_map = load_yaml(path)
    validate_module_map(module_map)
    return module_map


def validate_module_map(module_map: dict[str, Any]) -> None:
    if module_map.get("schema_version") != "1.0.0":
        raise ModuleMapError("Unsupported master module map schema.")
    if module_map.get("phases") != PHASES:
        raise ModuleMapError("Master module map phases must match runtime phase order.")
    modules = module_map.get("modules")
    if not isinstance(modules, list) or len(modules) != 20:
        raise ModuleMapError("Master module map must define exactly 20 modules.")
    ids = set()
    for module in modules:
        module_id = module.get("id")
        if not isinstance(module_id, str) or module_id in ids:
            raise ModuleMapError(f"Invalid or duplicate module id: {module_id}")
        ids.add(module_id)
        for field in ("system", "triggers", "phases", "capsule_path", "claims", "dependencies", "excludes"):
            if field not in module:
                raise ModuleMapError(f"Module {module_id} is missing {field}.")
        if not project_path(module["capsule_path"]).is_file():
            raise ModuleMapError(f"Module {module_id} capsule does not exist.")
        for source in module.get("full_yaml_paths", []):
            if not project_path(source).is_file():
                raise ModuleMapError(f"Module {module_id} source does not exist: {source}")
        if any(phase not in PHASES for phase in module["phases"]):
            raise ModuleMapError(f"Module {module_id} declares an unknown phase.")
    for module in modules:
        for dependency in module["dependencies"]:
            if dependency not in ids:
                raise ModuleMapError(f"Module {module['id']} has unknown dependency {dependency}.")


def route_modules(intent: dict[str, Any], module_map: dict[str, Any] | None = None) -> dict[str, Any]:
    module_map = module_map or load_module_map()
    features = set(intent.get("features", []))
    if intent.get("subject_kind") == "nonhuman":
        features.add("nonhuman_only")

    modules_by_id = {module["id"]: module for module in module_map["modules"]}
    selected = {
        module["id"]
        for module in module_map["modules"]
        if "always" in module["triggers"] or features.intersection(module["triggers"])
    }
    changed = True
    while changed:
        changed = False
        for module_id in list(selected):
            for dependency in modules_by_id[module_id]["dependencies"]:
                if dependency not in selected:
                    selected.add(dependency)
                    changed = True

    for module_id in list(selected):
        excludes = set(modules_by_id[module_id].get("excludes", []))
        if excludes.intersection(features):
            selected.remove(module_id)

    ordered = _topological_order(selected, modules_by_id)
    modules = [deepcopy(modules_by_id[module_id]) for module_id in ordered]
    phase_plan = []
    for phase in PHASES:
        phase_modules = [module["id"] for module in modules if phase in module["phases"]]
        phase_claims = sorted({claim for module in modules if phase in module["phases"] for claim in module["claims"]})
        phase_plan.append({"phase_id": phase, "modules": phase_modules, "claims": phase_claims})
    return {
        "schema_version": "1.0.0",
        "features": sorted(features),
        "modules": modules,
        "module_ids": [module["id"] for module in modules],
        "phase_plan": phase_plan,
    }


def _topological_order(selected: set[str], modules_by_id: dict[str, dict[str, Any]]) -> list[str]:
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(module_id: str) -> None:
        if module_id in visited:
            return
        if module_id in visiting:
            raise ModuleMapError(f"Module dependency cycle at {module_id}.")
        visiting.add(module_id)
        for dependency in modules_by_id[module_id].get("dependencies", []):
            if dependency in selected:
                visit(dependency)
        visiting.remove(module_id)
        visited.add(module_id)
        ordered.append(module_id)

    for module_id in sorted(selected):
        visit(module_id)
    return ordered
