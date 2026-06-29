"""Deterministic routing, execution-ledger, and quality-gate helpers.

The runtime treats a catalogued rule section as the unit of relevance.  An
agent receives an execution packet instead of independently deciding which
configuration files or phases it may skip.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "config" / "execution-catalog.yaml"
DEFAULT_QUALITY_CONTRACT = ROOT / "config" / "quality-contract.yaml"
DEFAULT_VISIBLE_EXPOSURE_CONTRACT = ROOT / "config" / "nsfw-visible-exposure-contract.yaml"
DEFAULT_EXPOSURE_ACTION_CONTROLLER = ROOT / "config" / "nsfw-exposure-action-controller.yaml"
DEFAULT_SEMANTIC_EXPOSURE_VISIBILITY = ROOT / "config" / "nsfw-semantic-exposure-visibility.yaml"
_ADULT_WHITELIST_INDEX = ROOT / "config" / "adult-character-whitelist" / "index.yaml"
_CATALOG_CACHE: dict[Path, tuple[tuple[tuple[str, int, int], ...], dict[str, Any]]] = {}
_PACKET_CACHE: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
_PRE_FILTER_CACHE: tuple[int, int, dict[str, Any]] | None = None
_WHITELIST_NAMES_CACHE: tuple[int, int, frozenset[str], frozenset[str], frozenset[str]] | None = None


class ExecutionError(ValueError):
    """A validation failure with structured evidence for failure-only traces."""

    def __init__(self, message: str, failures: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.failures = failures or []


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ExecutionError(f"{path} must contain a YAML object.")
    return data


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def relative_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def resolve_project_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as error:
        raise ExecutionError(f"Catalog path escapes project root: {value}") from error
    if not path.is_file():
        raise ExecutionError(f"Catalog source does not exist: {value}")
    return path


def pipeline_phase_ids() -> list[str]:
    pipeline = load_yaml(ROOT / "config" / "enhancement-pipeline.yaml")
    return [str(item["id"]) for item in pipeline["pipeline"]]


def active_source_paths() -> set[str]:
    """Return every source currently referenced by the manifest and pipeline."""

    manifest = load_yaml(ROOT / "config" / "_manifest.yaml")
    pipeline = load_yaml(ROOT / "config" / "enhancement-pipeline.yaml")
    paths = set(manifest["always_load"])
    for entry in manifest["conditional_load"].values():
        if "path" in entry:
            paths.add(entry["path"])
        paths.update(entry.get("paths", []))
    for route_paths in pipeline["module_routing"].values():
        paths.update(route_paths)
    return paths


def _node_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = catalog.get("rule_nodes")
    if not isinstance(nodes, list):
        raise ExecutionError("Catalog rule_nodes must be a list.")
    result: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            raise ExecutionError("Every catalog rule node needs a string id.")
        if node["id"] in result:
            raise ExecutionError(f"Duplicate catalog rule node: {node['id']}")
        result[node["id"]] = node
    return result


def _node_source_paths(node: dict[str, Any]) -> set[str]:
    sources = node.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ExecutionError(f"Rule node {node['id']} must define non-empty sources.")
    result: set[str] = set()
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("path"), str):
            raise ExecutionError(f"Rule node {node['id']} has an invalid source entry.")
        result.add(source["path"])
    return result


def validate_catalog(catalog: dict[str, Any]) -> None:
    if catalog.get("schema_version") != "1.0.0":
        raise ExecutionError("Unsupported execution catalog schema version.")
    if catalog.get("mode") != "fixed_complete_semantic_closure":
        raise ExecutionError("Catalog must use fixed_complete_semantic_closure mode.")
    if catalog.get("phase_ids") != pipeline_phase_ids():
        raise ExecutionError("Catalog phase_ids must match enhancement-pipeline.yaml exactly.")

    nodes = _node_map(catalog)
    catalog_paths: set[str] = set()
    for node in nodes.values():
        phases = node.get("phases")
        triggers = node.get("triggers")
        claims = node.get("claims")
        if not isinstance(phases, list) or not phases or any(phase not in catalog["phase_ids"] for phase in phases):
            raise ExecutionError(f"Rule node {node['id']} has invalid phases.")
        if not isinstance(triggers, list) or not triggers:
            raise ExecutionError(f"Rule node {node['id']} must define triggers.")
        if not isinstance(claims, list) or not claims:
            raise ExecutionError(f"Rule node {node['id']} must define claims.")
        for dependency in node.get("requires", []):
            if dependency not in nodes:
                raise ExecutionError(f"Rule node {node['id']} requires unknown node {dependency}.")
        for conflict in node.get("conflicts", []):
            if conflict not in nodes:
                raise ExecutionError(f"Rule node {node['id']} conflicts with unknown node {conflict}.")
        for source in node.get("sources", []):
            load_mode = source.get("load_mode", "inline")
            if load_mode not in {"inline", "reference_only"}:
                raise ExecutionError(f"Rule node {node['id']} has invalid load_mode for {source['path']}.")
            if load_mode == "reference_only":
                materialize_at_phase = source.get("materialize_at_phase")
                activate_when = source.get("activate_when")
                if materialize_at_phase not in catalog["phase_ids"]:
                    raise ExecutionError(f"Rule node {node['id']} has invalid materialize_at_phase for {source['path']}.")
                if not isinstance(activate_when, list) or not activate_when or not all(isinstance(item, str) for item in activate_when):
                    raise ExecutionError(f"Rule node {node['id']} has invalid activate_when for {source['path']}.")
            path = resolve_project_path(source["path"])
            catalog_paths.add(source["path"])
            sections = source.get("sections")
            if sections is not None:
                document = load_yaml(path)
                if not isinstance(sections, list) or not sections:
                    raise ExecutionError(f"Rule node {node['id']} has invalid sections for {source['path']}.")
                missing = [section for section in sections if section not in document]
                if missing:
                    raise ExecutionError(f"Rule node {node['id']} references missing sections in {source['path']}: {missing}")

    missing_sources = active_source_paths() - catalog_paths
    if missing_sources:
        raise ExecutionError("Catalog does not cover active sources: " + ", ".join(sorted(missing_sources)))

    def visit(node_id: str, active: set[str], visited: set[str]) -> None:
        if node_id in active:
            raise ExecutionError(f"Catalog dependency cycle detected at {node_id}.")
        if node_id in visited:
            return
        active.add(node_id)
        for child in nodes[node_id].get("requires", []):
            visit(child, active, visited)
        active.remove(node_id)
        visited.add(node_id)

    visited: set[str] = set()
    for node_id in nodes:
        visit(node_id, set(), visited)


def _catalog_fingerprint(path: Path, catalog: dict[str, Any]) -> tuple[tuple[str, int, int], ...]:
    paths = {path.resolve(), ROOT / "config" / "_manifest.yaml", ROOT / "config" / "enhancement-pipeline.yaml"}
    paths.update(resolve_project_path(source["path"]) for node in catalog["rule_nodes"] for source in node["sources"])
    return tuple(sorted((str(item), item.stat().st_mtime_ns, item.stat().st_size) for item in paths))


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    path = path.resolve()
    catalog = load_yaml(path)
    fingerprint = _catalog_fingerprint(path, catalog)
    cached = _CATALOG_CACHE.get(path)
    if cached and cached[0] == fingerprint:
        return cached[1]
    validate_catalog(catalog)
    _CATALOG_CACHE[path] = (fingerprint, catalog)
    return catalog


FEATURE_PATTERNS: dict[str, tuple[str, ...]] = {
    "image_edit": ("edit", "revise", "repair", "replace", "change only", "reference image", "source image"),
    "named_character": ("whitelist", "named character", "canonical character", "character profile"),
    "adult_human_scene": ("adult", "woman", "man", "human", "humanoid", "character", "person", "nude", "nsfw"),
    "dynamic_action_or_interaction": ("motion", "dynamic", "turning", "impact", "peak", "action", "interaction", "pose", "movement", "duo", "pov", "bdsm"),
    "material_or_environment_response": ("wet", "damp", "water", "steam", "rain", "silk", "latex", "fabric", "bedding", "glass", "reflective", "moisture"),
    "scene_and_visual_enrichment": ("scene", "interior", "exterior", "street", "room", "balcony", "bathroom", "shower", "bedroom", "environment"),
    "visual_cinematography": ("camera", "lighting", "light", "portrait", "wide", "close-up", "composition", "cinematic"),
    "style_realism": ("anime", "illustration", "cel-shaded"),
    "standing_pose": ("standing", "stand ", "standing pose"),
    "seated_pose": ("seated", "sitting", "sit ", "on a sofa", "on a chair"),
    "reclining_pose": ("reclining", "lying", "lying down", "on bedding", "on a bed"),
    "wardrobe_unspecified": (),
    "wardrobe_specified": (),
    "generic_subject": (),
    "ip_character": ("whitelist", "named character", "canonical character", "character profile"),
}
NONHUMAN_MARKERS = ("landscape", "object", "still life", "architecture", "vehicle", "animal", "mountain", "lake")


def decision_pre_filter() -> dict[str, Any]:
    """Load the compact deterministic router contract, never its leaf libraries."""

    global _PRE_FILTER_CACHE
    path = ROOT / "config" / "core-knowledge.yaml"
    stat = path.stat()
    if _PRE_FILTER_CACHE and _PRE_FILTER_CACHE[:2] == (stat.st_mtime_ns, stat.st_size):
        return _PRE_FILTER_CACHE[2]
    value = load_yaml(path).get("decision_pre_filter")
    if not isinstance(value, dict) or value.get("schema_version") != "1.0.0":
        raise ExecutionError("core-knowledge.yaml must define decision_pre_filter schema 1.0.0.")
    _PRE_FILTER_CACHE = (stat.st_mtime_ns, stat.st_size, value)
    return value


def _load_whitelist_name_tokens() -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Return (full_names, first_name_tokens, single_names) from the adult whitelist index.

    Results are cached by file mtime+size to avoid repeated reads.
    """
    global _WHITELIST_NAMES_CACHE
    path = _ADULT_WHITELIST_INDEX
    stat = path.stat()
    if _WHITELIST_NAMES_CACHE and _WHITELIST_NAMES_CACHE[:2] == (stat.st_mtime_ns, stat.st_size):
        return _WHITELIST_NAMES_CACHE[2:]

    index = load_yaml(path)
    characters = index.get("characters") if isinstance(index, dict) else []
    full_names: set[str] = set()
    first_tokens: set[str] = set()
    single_names: set[str] = set()

    for entry in characters if isinstance(characters, list) else []:
        name = str(entry.get("name", "")).casefold().strip()
        if not name:
            continue
        full_names.add(name)
        parts = name.split()
        if len(parts) == 1:
            if len(parts[0]) >= 4:
                single_names.add(parts[0])
        else:
            if len(parts[0]) >= 3:
                first_tokens.add(parts[0])

    frozen_full = frozenset(full_names)
    frozen_first = frozenset(first_tokens)
    frozen_single = frozenset(single_names)
    _WHITELIST_NAMES_CACHE = (stat.st_mtime_ns, stat.st_size, frozen_full, frozen_first, frozen_single)
    return frozen_full, frozen_first, frozen_single


def _whitelisted_character_in_request(text: str) -> bool:
    """Return True when the request (casefolded) references a whitelisted adult character."""
    full_names, first_tokens, single_names = _load_whitelist_name_tokens()
    tokens = set(text.split())

    # 1. Full name as substring (handles "Aerith Gainsborough", "Cloud Strife")
    for name in full_names:
        if name in text:
            return True

    # 2. First-name token from multi-word names (handles "Aerith", "Tifa", "Cloud")
    if tokens & first_tokens:
        return True

    # 3. Single-word names >= 4 chars (handles "Sephiroth", "Lightning", "Beatrix")
    if tokens & single_names:
        return True

    return False


def infer_features(request: str, provided_features: Iterable[str] = ()) -> list[str]:
    text = request.casefold()
    features = {"always", *[str(feature) for feature in provided_features]}
    pre_filter = decision_pre_filter()
    configured_patterns = pre_filter.get("feature_markers", {})
    if not isinstance(configured_patterns, dict):
        raise ExecutionError("decision_pre_filter.feature_markers must be a mapping.")
    patterns = {
        feature: tuple(str(marker).casefold() for marker in configured_patterns.get(feature, FEATURE_PATTERNS[feature]))
        for feature in FEATURE_PATTERNS
    }
    _whitelist_hit = _whitelisted_character_in_request(text)
    nonhuman_only = any(marker in text for marker in NONHUMAN_MARKERS) and not any(
        marker in text for marker in patterns["adult_human_scene"]
    ) and not _whitelist_hit
    for feature, markers in patterns.items():
        if feature == "adult_human_scene" and nonhuman_only:
            continue
        if feature in ("wardrobe_unspecified", "wardrobe_specified", "generic_subject"):
            continue
        if any(marker in text for marker in markers):
            features.add(feature)
    # Whitelisted character detection: if the request names a confirmed-adult
    # character, auto-trigger adult_human_scene even when no explicit keyword
    # like "adult" or "character" appears in the raw prompt.
    if _whitelist_hit and not nonhuman_only:
        features.add("adult_human_scene")
        features.add("ip_character")
        features.add("named_character")
    # Wardrobe detection: check if any clothing keyword is present
    CLOTHING_MARKERS = (
        "wearing", "dressed", "clothed", "outfit", "dress", "shirt", "skirt", "pants",
        "shorts", "jacket", "coat", "blouse", "top", "bra", "panties", "underwear",
        "bikini", "swimsuit", "lingerie", "uniform", "robe", "suit", "jeans",
        "leggings", "stockings", "boots", "shoes", "heels", "hat", "gloves",
        "scarf", "belt", "tie", "bodysuit", "corset", "thong", "g-string",
        "camisole", "tank top", "tube top", "crop top", "mini skirt", "hot pants",
    )
    is_human = "adult_human_scene" in features and not nonhuman_only
    is_ip = "ip_character" in features
    if is_human:
        wardrobe_specified = any(marker in text for marker in CLOTHING_MARKERS)
        if wardrobe_specified:
            features.add("wardrobe_specified")
        else:
            features.add("wardrobe_unspecified")
            if is_ip:
                features.add("ip_character")
            else:
                features.add("generic_subject")
    return sorted(features)


def _topological_order(node_ids: set[str], nodes: dict[str, dict[str, Any]]) -> list[str]:
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise ExecutionError(f"Catalog dependency cycle detected at {node_id}.")
        if node_id in visited:
            return
        visiting.add(node_id)
        for dependency in nodes[node_id].get("requires", []):
            if dependency in node_ids:
                visit(dependency)
        visiting.remove(node_id)
        visited.add(node_id)
        ordered.append(node_id)

    for node_id in sorted(node_ids):
        visit(node_id)
    return ordered


def select_rule_nodes(catalog: dict[str, Any], features: Iterable[str]) -> list[dict[str, Any]]:
    nodes = _node_map(catalog)
    feature_set = set(features)
    selected = {node_id for node_id, node in nodes.items() if feature_set.intersection(node["triggers"])}
    pending = list(selected)
    while pending:
        node_id = pending.pop()
        for dependency in nodes[node_id].get("requires", []):
            if dependency not in selected:
                selected.add(dependency)
                pending.append(dependency)
    for node_id in selected:
        conflicts = selected.intersection(nodes[node_id].get("conflicts", []))
        if conflicts:
            raise ExecutionError(f"Conflicting selected rule nodes: {node_id}, {sorted(conflicts)[0]}")
    return [nodes[node_id] for node_id in _topological_order(selected, nodes)]


METADATA_KEYS = ("schema_version", "version", "name", "description", "purpose")


def _source_content(path: Path, sections: Any) -> tuple[bytes, str]:
    raw = path.read_bytes()
    document = load_yaml(path)
    if sections is None:
        content = document
    else:
        content = {key: document[key] for key in METADATA_KEYS if key in document}
        content.update({section: document[section] for section in sections})
    return raw, yaml.safe_dump(content, allow_unicode=True, sort_keys=False)


def extract_source(source: dict[str, Any], *, force_inline: bool = False) -> dict[str, Any]:
    """Extract inline leaf content or a non-agent-visible deferred descriptor."""

    path = resolve_project_path(source["path"])
    sections = source.get("sections")
    raw, rendered = _source_content(path, sections)
    load_mode = source.get("load_mode", "inline")
    base = {
        "path": source["path"],
        "sections": sections or ["__entire_document__"],
        "declared_sections": sections,
        "source_hash": digest(raw),
        "context_hash": digest(rendered),
    }
    if load_mode == "reference_only" and not force_inline:
        return {
            **base,
            "reference_only": True,
            "reference_id": source.get("reference_id") or f"{source['path']}::{','.join(sections or ['__entire_document__'])}",
            "materialize_at_phase": source["materialize_at_phase"],
            "activate_when": source["activate_when"],
            "line_count": 0,
            "materialized_line_count": rendered.count("\n"),
        }
    return {**base, "line_count": rendered.count("\n"), "content_yaml": rendered}


def _reference_is_active(reference: dict[str, Any], features: Iterable[str]) -> bool:
    activation = set(reference.get("activate_when", []))
    return "always" in activation or bool(activation.intersection(features))


def materialize_phase_context(packet: dict[str, Any], phase_id: str) -> dict[str, Any]:
    """Load every packet-mandated deferred source for one phase deterministically."""

    phase_ids = [phase["id"] for phase in packet.get("phases", [])]
    if phase_id not in phase_ids:
        raise ExecutionError(f"Unknown packet phase for materialization: {phase_id}")
    materialized: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for reference in packet.get("deferred_references", []):
        if reference.get("materialize_at_phase") != phase_id or not _reference_is_active(reference, packet.get("features", [])):
            continue
        source = extract_source({"path": reference["path"], "sections": reference.get("declared_sections")}, force_inline=True)
        if source["source_hash"] != reference.get("source_hash") or source["context_hash"] != reference.get("context_hash"):
            raise ExecutionError("Deferred reference changed after packet compilation.", [_failure("reference_hash_stale", "Deferred reference source or context hash changed.", reference_id=reference["reference_id"])])
        materialized.append(source)
        receipts.append(
            {
                "reference_id": reference["reference_id"],
                "path": reference["path"],
                "phase_id": phase_id,
                "source_hash": source["source_hash"],
                "context_hash": source["context_hash"],
                "status": "loaded",
            }
        )
    return {"phase_id": phase_id, "sources": materialized, "reference_access": receipts}


def _all_catalog_source_lines(catalog: dict[str, Any]) -> int:
    paths = {source["path"] for node in catalog["rule_nodes"] for source in node["sources"]}
    return sum(resolve_project_path(path).read_text(encoding="utf-8").count("\n") + 1 for path in paths)


def compile_execution_packet(
    request: str,
    provided_features: Iterable[str] = (),
    catalog_path: Path = DEFAULT_CATALOG,
) -> dict[str, Any]:
    if not isinstance(request, str) or not request.strip():
        raise ExecutionError("A non-empty request is required to compile an execution packet.")
    provided_features = tuple(provided_features)
    catalog = load_catalog(catalog_path)
    known_features = {trigger for node in catalog["rule_nodes"] for trigger in node["triggers"]}
    unknown_features = sorted(set(provided_features) - known_features)
    if unknown_features:
        raise ExecutionError("Unknown conservative routing features: " + ", ".join(unknown_features))
    features = infer_features(request, provided_features)
    cache_key = (digest(canonical_json(catalog)), request.strip(), tuple(features))
    cached_packet = _PACKET_CACHE.get(cache_key)
    if cached_packet is not None:
        return deepcopy(cached_packet)
    nodes = select_rule_nodes(catalog, features)
    context: list[dict[str, Any]] = []
    deferred_references: list[dict[str, Any]] = []
    for node in nodes:
        inline_sources: list[dict[str, Any]] = []
        context.append(
            {
                "node_id": node["id"],
                "claims": node["claims"],
                "sources": inline_sources,
            }
        )
        for source in node["sources"]:
            extracted = extract_source(source)
            if extracted.get("reference_only"):
                deferred_references.append({"node_id": node["id"], "claims": node["claims"], **extracted})
            else:
                inline_sources.append(extracted)
    required_claims = sorted({claim for node in nodes for claim in node["claims"]})
    phases = []
    for phase_id in catalog["phase_ids"]:
        phase_nodes = [node["id"] for node in nodes if phase_id in node["phases"]]
        phase_claims = sorted({claim for node in nodes if phase_id in node["phases"] for claim in node["claims"]})
        phases.append({"id": phase_id, "required_nodes": phase_nodes, "required_claims": phase_claims})
    broad_lines = _all_catalog_source_lines(catalog)
    visible_lines = sum(source["line_count"] for item in context for source in item["sources"])
    fully_materialized_lines = visible_lines + sum(
        reference["materialized_line_count"] for reference in deferred_references if _reference_is_active(reference, features)
    )
    packet_seed = {
        "catalog_hash": digest(canonical_json(catalog)),
        "request": request.strip(),
        "features": features,
        "selected_node_ids": [node["id"] for node in nodes],
        "context_hashes": [source["context_hash"] for item in context for source in item["sources"]] + [reference["context_hash"] for reference in deferred_references],
    }
    try:
        catalog_reference = relative_path(catalog_path.resolve())
    except ValueError:
        catalog_reference = str(catalog_path.resolve())
    packet = {
        "schema_version": "1.0.0",
        "mode": catalog["mode"],
        "catalog_path": catalog_reference,
        "catalog_hash": packet_seed["catalog_hash"],
        "packet_id": digest(canonical_json(packet_seed))[:20],
        "request": request.strip(),
        "features": features,
        "selected_nodes": [
            {
                "id": node["id"],
                "phases": node["phases"],
                "claims": node["claims"],
                "requires": node.get("requires", []),
                "cost_class": node["cost_class"],
            }
            for node in nodes
        ],
        "required_claims": required_claims,
        "phases": phases,
        "compiled_context": context,
        "deferred_references": deferred_references,
        "metrics": {
            "broad_agent_visible_lines": broad_lines,
            "compiled_agent_visible_lines": visible_lines,
            "context_reduction_percent": round((1 - visible_lines / broad_lines) * 100, 2) if broad_lines else 0.0,
            "fully_materialized_agent_visible_lines": fully_materialized_lines,
            "initial_context_reduction_percent": round((1 - visible_lines / fully_materialized_lines) * 100, 2) if fully_materialized_lines else 0.0,
        },
    }
    packet["packet_hash"] = digest(canonical_json(packet))
    packet["execution_record_template"] = execution_record_template(packet)
    _PACKET_CACHE[cache_key] = deepcopy(packet)
    return packet


def execution_record_template(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "packet_id": packet["packet_id"],
        "packet_hash": packet["packet_hash"],
        "phases": [
            {"id": phase["id"], "status": "pending", "applied_nodes": [], "outputs": [], "claims": []}
            for phase in packet["phases"]
        ],
        "claims": [],
        "provenance": [],
        "exposure_contract": None,
        "exposure_action_plan": None,
        "exposure_geometry_plan": None,
        "exposure_geometry_result": None,
        "semantic_exposure_visibility_plan": None,
        "semantic_exposure_visibility_result": None,
        "exposure_feasibility_review": None,
        "recomposition_attempts": [],
        "reference_access": [],
        "prompt_pack": {},
    }


def _failure(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def _positive_prompt_fields(prompt_pack: dict[str, str]) -> dict[str, str]:
    return {
        field: value.casefold()
        for field, value in prompt_pack.items()
        if field.endswith("_positive_prompt") and isinstance(value, str)
    }


def visible_exposure_policy(path: Path = DEFAULT_VISIBLE_EXPOSURE_CONTRACT) -> dict[str, Any]:
    policy = load_yaml(path)
    if policy.get("schema_version") != "1.0.0" or policy.get("name") != "nsfw-visible-exposure-contract":
        raise ExecutionError("Unsupported visible exposure contract.")
    return policy


def _require_list(value: Any, field: str, failures: list[dict[str, Any]]) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        failures.append(_failure("exposure_contract_schema", "Exposure-contract field must be a list of strings.", field=field))
        return set()
    return set(value)


def _action_prompt_terms(action: str) -> tuple[str, ...]:
    return {
        "partially_removed": ("partially removed", "partially remove"),
        "pulled_aside": ("pulled aside", "pull aside", "pulling open"),
        "unbuttoned_or_opened": ("unbuttoned", "opened"),
        "slipped_or_lowered": ("slipped", "lowered"),
        "displaced_by_pose_or_grip": ("displaced", "pulled", "grip"),
        "wet_translucent_cling": ("wet", "sheer", "translucent"),
    }[action]


def validate_visible_exposure_contract(value: Any, prompt_pack: dict[str, str]) -> None:
    """Require visible adult exposure evidence for a compiled adult-human packet."""

    policy = visible_exposure_policy()
    specification = policy["visible_exposure_contract"]
    resolution = policy["resolution"]
    failures: list[dict[str, Any]] = []
    if not isinstance(value, dict):
        raise ExecutionError(
            "Visible exposure contract failed validation.",
            [_failure("visible_exposure_contract_missing", "Eligible human scene is missing exposure_contract.")],
        )

    required_fields = specification["required_fields"]
    missing_fields = [field for field in required_fields if field not in value]
    if missing_fields:
        failures.append(_failure("visible_exposure_contract_missing_fields", "Exposure contract is incomplete.", missing_fields=missing_fields))

    subject = value.get("subject_presentation")
    wardrobe_state = value.get("wardrobe_state")
    requirement = value.get("exposure_requirement")
    evidence_mode = value.get("evidence_mode")
    target = value.get("evidence_target")
    action = value.get("garment_transformation_action")

    if subject not in specification["subject_presentations"]:
        failures.append(_failure("exposure_subject_presentation", "Exposure contract has an invalid subject presentation.", value=subject))
    if wardrobe_state not in specification["wardrobe_states"]:
        failures.append(_failure("exposure_wardrobe_state", "Exposure contract has an invalid wardrobe state.", value=wardrobe_state))
    if evidence_mode not in specification["evidence_modes"]:
        failures.append(_failure("exposure_evidence_mode", "Exposure contract has an invalid evidence mode.", value=evidence_mode))

    required_guards = set(specification["required_camera_visibility_guards"])
    actual_guards = _require_list(value.get("camera_visibility_guard"), "camera_visibility_guard", failures)
    missing_guards = sorted(required_guards - actual_guards)
    if missing_guards:
        failures.append(_failure("exposure_visibility_guard", "Exposure target is not protected by every camera visibility guard.", missing_guards=missing_guards))

    required_substitutions = set(specification["required_forbidden_substitutions"])
    actual_substitutions = _require_list(value.get("forbidden_substitutions"), "forbidden_substitutions", failures)
    missing_substitutions = sorted(required_substitutions - actual_substitutions)
    if missing_substitutions:
        failures.append(_failure("exposure_forbidden_substitutions", "Exposure contract does not reject every invalid substitute.", missing_substitutions=missing_substitutions))

    if wardrobe_state in ("unspecified_wardrobe_generic", "unspecified_wardrobe"):
        generic_rule = resolution["unspecified_wardrobe"]["generic_subject"]
        if requirement != generic_rule["exposure_requirement"]:
            failures.append(_failure("exposure_requirement", "Generic unspecified wardrobe must resolve to partial_nudity_required.", actual=requirement))
    elif wardrobe_state == "unspecified_wardrobe_ip":
        ip_rule = resolution["unspecified_wardrobe"]["ip_character"]
        if requirement != ip_rule["exposure_requirement"]:
            failures.append(_failure("exposure_requirement", "IP character unspecified wardrobe must resolve to partial_nudity_required.", actual=requirement))
    elif wardrobe_state == "explicit_wardrobe":
        expected = resolution["explicit_wardrobe"]
        if requirement != expected["exposure_requirement"]:
            failures.append(_failure("exposure_requirement", "Explicit wardrobe must resolve to partial_nudity_required.", actual=requirement))
        if action not in expected["allowed_garment_transformation_actions"]:
            failures.append(_failure("exposure_garment_action", "Explicit wardrobe needs a concrete allowed garment transformation.", actual=action))

    if subject == "female_feminine":
        if target not in resolution["female_feminine_evidence"]["allowed_targets"]:
            failures.append(_failure("exposure_evidence_target", "Female/feminine exposure requires nipple or vulva evidence.", actual=target))
    elif subject in {"male_masculine", "unspecified_gender"} and target != "adult_bare_anatomy":
        failures.append(_failure("exposure_evidence_target", "Non-feminine exposure uses adult_bare_anatomy in this release.", actual=target))

    positive_prompts = _positive_prompt_fields(prompt_pack)
    if subject == "female_feminine" and isinstance(target, str):
        for field, prompt in positive_prompts.items():
            if target.casefold() not in prompt:
                failures.append(_failure("exposure_prompt_evidence", "Positive prompt does not name the selected evidence target.", field=field, target=target))
            elif prompt.find(target.casefold()) > 320:
                failures.append(_failure("exposure_prompt_order", "Selected evidence target must appear in the early subject description.", field=field, target=target))
            if "visible" not in prompt or ("unobscured" not in prompt and "in frame" not in prompt):
                failures.append(_failure("exposure_prompt_visibility", "Positive prompt does not make selected evidence visibly in-frame and unobscured.", field=field, target=target))
        if wardrobe_state in ("unspecified_wardrobe", "unspecified_wardrobe_generic", "unspecified_wardrobe_ip") and any("nude" not in prompt and "bare" not in prompt for prompt in positive_prompts.values()):
            failures.append(_failure("exposure_prompt_nudity", "Unspecified wardrobe must state the adult presentation in every positive prompt."))
        if evidence_mode == "sheer_visible_anatomy" and any("sheer" not in prompt and "translucent" not in prompt for prompt in positive_prompts.values()):
            failures.append(_failure("exposure_sheer_evidence", "Sheer evidence must name sheer or translucent material in every positive prompt.", target=target))
    elif subject in {"male_masculine", "unspecified_gender"}:
        for field, prompt in positive_prompts.items():
            if "nude" not in prompt and "bare" not in prompt:
                failures.append(_failure("exposure_prompt_evidence", "Positive prompt does not state the required bare adult presentation.", field=field))

    if wardrobe_state in ("explicit_wardrobe", "unspecified_wardrobe", "unspecified_wardrobe_generic", "unspecified_wardrobe_ip"):
        allowed = resolution.get(wardrobe_state, {}).get("allowed_garment_transformation_actions", [])
        if not allowed and wardrobe_state in resolution.get("unspecified_wardrobe", {}):
            allowed = resolution["unspecified_wardrobe"].get("generic_subject", {}).get("allowed_garment_transformation_actions", [])
        if isinstance(action, str) and action not in allowed:
            failures.append(_failure("exposure_garment_action", "Garment transformation action is not allowed for this wardrobe state.", actual=action, allowed=allowed))

    if failures:
        raise ExecutionError("Visible exposure contract failed validation.", failures)


def exposure_action_policy(path: Path = DEFAULT_EXPOSURE_ACTION_CONTROLLER) -> dict[str, Any]:
    policy = load_yaml(path)
    if policy.get("schema_version") != "1.0.0" or policy.get("name") != "nsfw-exposure-action-controller":
        raise ExecutionError("Unsupported exposure action controller.")
    return policy


def _require_nonempty_string(value: Any, field: str, failures: list[dict[str, Any]]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        failures.append(_failure("exposure_action_schema", "Exposure action field must be a non-empty string.", field=field))
        return None
    return value


def _prompt_contains_all(prompt: str, terms: Iterable[str]) -> bool:
    return all(term.casefold() in prompt for term in terms)


def _prompt_contains_any(prompt: str, terms: Iterable[str]) -> bool:
    return any(term.casefold() in prompt for term in terms)


def validate_exposure_action_plan(
    value: Any,
    exposure_contract: Any,
    feasibility_review: Any,
    recomposition_attempts: Any,
    prompt_pack: dict[str, str],
) -> None:
    """Validate a target-compatible action, final state, and recovery receipt."""

    policy = exposure_action_policy()
    plan_schema = policy["exposure_action_plan"]
    matrix = policy["compatibility_matrix"]
    material_rules = policy["material_requirements"]
    review_schema = policy["feasibility_review"]
    failures: list[dict[str, Any]] = []
    if not isinstance(value, dict):
        raise ExecutionError(
            "Exposure action plan failed validation.",
            [_failure("exposure_action_plan_missing", "Eligible human scene is missing exposure_action_plan.")],
        )
    if not isinstance(exposure_contract, dict):
        raise ExecutionError(
            "Exposure action plan failed validation.",
            [_failure("exposure_action_contract_missing", "Exposure action cannot be validated without exposure_contract.")],
        )

    missing_fields = [field for field in plan_schema["required_fields"] if field not in value]
    if missing_fields:
        failures.append(_failure("exposure_action_plan_missing_fields", "Exposure action plan is incomplete.", missing_fields=missing_fields))

    target = _require_nonempty_string(value.get("primary_target"), "primary_target", failures)
    route = _require_nonempty_string(value.get("route"), "route", failures)
    garment_zone = _require_nonempty_string(value.get("garment_zone"), "garment_zone", failures)
    action = _require_nonempty_string(value.get("action"), "action", failures)
    action_anchor = _require_nonempty_string(value.get("action_anchor"), "action_anchor", failures)
    end_state = _require_nonempty_string(value.get("end_state"), "end_state", failures)
    fallback_route = _require_nonempty_string(value.get("fallback_route"), "fallback_route", failures)
    camera_proof = _require_list(value.get("camera_proof"), "camera_proof", failures)

    allowed_routes = set(plan_schema["routes"])
    if route not in allowed_routes:
        failures.append(_failure("exposure_action_route", "Exposure action has an invalid route.", actual=route))
    if fallback_route not in allowed_routes | {"block_delivery"}:
        failures.append(_failure("exposure_action_fallback", "Exposure action has an invalid fallback route.", actual=fallback_route))
    elif fallback_route == route:
        failures.append(_failure("exposure_action_fallback", "Exposure action fallback must differ from its active route.", actual=fallback_route))
    if target != exposure_contract.get("evidence_target"):
        failures.append(
            _failure(
                "exposure_action_target_mismatch",
                "Exposure action target must equal the selected visible evidence target.",
                action_target=target,
                contract_target=exposure_contract.get("evidence_target"),
            )
        )

    required_camera_proof = set(plan_schema["camera_proof_required"])
    missing_camera_proof = sorted(required_camera_proof - camera_proof)
    if missing_camera_proof:
        failures.append(_failure("exposure_action_camera_proof", "Exposure action lacks required camera proof.", missing_fields=missing_camera_proof))

    action_definition: dict[str, Any] | None = None
    if isinstance(route, str) and isinstance(target, str) and route in matrix and target in matrix[route]:
        target_rules = matrix[route][target]
        if garment_zone != target_rules["garment_zone"]:
            failures.append(
                _failure(
                    "exposure_action_garment_zone",
                    "Exposure action garment zone is incompatible with its target and route.",
                    target=target,
                    route=route,
                    expected=target_rules["garment_zone"],
                    actual=garment_zone,
                )
            )
        if isinstance(action, str):
            action_definition = target_rules["actions"].get(action)
            if action_definition is None:
                failures.append(_failure("exposure_action_incompatible", "Exposure action is incompatible with its target and garment zone.", target=target, route=route, action=action))
    elif isinstance(route, str) and route in matrix:
        failures.append(_failure("exposure_action_target_mismatch", "Exposure action target is not supported by its selected route.", target=target, route=route))

    if action_definition is not None:
        if end_state != action_definition["end_state"]:
            failures.append(
                _failure(
                    "exposure_action_end_state",
                    "Exposure action end state does not guarantee the selected target is exposed or discernible.",
                    expected=action_definition["end_state"],
                    actual=end_state,
                )
            )
        if exposure_contract.get("garment_transformation_action") != action_definition["contract_transformation_action"]:
            failures.append(
                _failure(
                    "exposure_action_contract_action",
                    "Exposure action does not match the resolved wardrobe transformation.",
                    expected=action_definition["contract_transformation_action"],
                    actual=exposure_contract.get("garment_transformation_action"),
                )
            )

    material_cause = value.get("material_cause_when_relevant")
    if route in {"direct_bare_no_wardrobe", "direct_garment_action"}:
        if material_cause != material_rules[route]:
            failures.append(_failure("exposure_action_material", "Direct exposure route must not claim a material-only reveal cause.", actual=material_cause))
        if route == "direct_garment_action" and action_anchor == "not_applicable":
            failures.append(_failure("exposure_action_anchor", "Direct garment action needs a physical hand, pose, or garment anchor."))
    elif route == "sheer_material_action":
        required_material = material_rules[route]["required_fields"]
        if not isinstance(material_cause, dict):
            failures.append(_failure("exposure_action_material", "Sheer route requires material cause details."))
        else:
            missing_material = [field for field in required_material if not isinstance(material_cause.get(field), str) or not material_cause[field].strip()]
            if missing_material:
                failures.append(_failure("exposure_action_material", "Sheer route is missing material cause details.", missing_fields=missing_material))
            elif material_cause.get("fabric_state") != material_rules[route]["fabric_state"]:
                failures.append(_failure("exposure_action_material", "Sheer route needs wet_or_translucent fabric state.", actual=material_cause.get("fabric_state")))
        if action_anchor == "not_applicable":
            failures.append(_failure("exposure_action_anchor", "Sheer route needs a physical fabric adhesion, stretch, or pose anchor."))

    positive_prompts = _positive_prompt_fields(prompt_pack)
    if action_definition is not None:
        for field, prompt in positive_prompts.items():
            if not _prompt_contains_all(prompt, action_definition["action_terms"]):
                failures.append(_failure("exposure_action_prompt_action", "Positive prompt does not describe the compatible physical exposure action.", field=field, action=action))
            elif any(prompt.find(term.casefold()) > 420 for term in action_definition["action_terms"]):
                failures.append(_failure("exposure_action_prompt_order", "Exposure action must appear in the early subject description.", field=field, action=action))
            if not _prompt_contains_any(prompt, action_definition["end_state_terms"]):
                failures.append(_failure("exposure_action_prompt_end_state", "Positive prompt does not describe the action's exposed or discernible end state.", field=field, end_state=end_state))
            elif not any(0 <= prompt.find(term.casefold()) <= 420 for term in action_definition["end_state_terms"]):
                failures.append(_failure("exposure_action_prompt_order", "Exposure end state must appear in the early subject description.", field=field, end_state=end_state))

    if not isinstance(feasibility_review, dict):
        failures.append(_failure("exposure_feasibility_review_missing", "Eligible human scene is missing exposure_feasibility_review."))
    else:
        missing_review = [field for field in review_schema["required_fields"] if field not in feasibility_review]
        if missing_review:
            failures.append(_failure("exposure_feasibility_review_schema", "Exposure feasibility review is incomplete.", missing_fields=missing_review))
        if feasibility_review.get("status") != "passed":
            failures.append(_failure("exposure_feasibility_review", "Exposure feasibility review must pass before delivery.", actual=feasibility_review.get("status")))
        for field in review_schema["required_pass_values"]:
            if feasibility_review.get(field) != "pass":
                failures.append(_failure("exposure_feasibility_check", "Exposure feasibility check did not pass.", check=field, actual=feasibility_review.get(field)))
        attempt_count = feasibility_review.get("attempt_count")
        if not isinstance(attempt_count, int) or attempt_count < 0 or attempt_count > review_schema["maximum_recomposition_attempts"]:
            failures.append(_failure("exposure_recomposition_attempt_count", "Exposure feasibility review has an invalid recomposition attempt count.", actual=attempt_count))

    if not isinstance(recomposition_attempts, list):
        failures.append(_failure("exposure_recomposition_schema", "recomposition_attempts must be a list."))
        recomposition_attempts = []
    if len(recomposition_attempts) > review_schema["maximum_recomposition_attempts"]:
        failures.append(_failure("exposure_recomposition_limit", "Exposure recomposition exceeded the maximum attempt count.", actual=len(recomposition_attempts)))
    if isinstance(feasibility_review, dict) and feasibility_review.get("attempt_count") != len(recomposition_attempts):
        failures.append(_failure("exposure_recomposition_receipt", "Feasibility review attempt count must match recomposition receipts.", expected=len(recomposition_attempts), actual=feasibility_review.get("attempt_count")))
    for expected_attempt, entry in enumerate(recomposition_attempts, start=1):
        if not isinstance(entry, dict):
            failures.append(_failure("exposure_recomposition_schema", "Every recomposition receipt must be an object.", attempt=expected_attempt))
            continue
        if entry.get("attempt") != expected_attempt or entry.get("outcome") != "recomposed":
            failures.append(_failure("exposure_recomposition_receipt", "Recomposition receipt has invalid order or outcome.", attempt=expected_attempt))
        reasons = entry.get("failure_reasons")
        if not isinstance(reasons, list) or not reasons or not all(isinstance(reason, str) and reason for reason in reasons):
            failures.append(_failure("exposure_recomposition_receipt", "Recomposition receipt needs non-empty failure reasons.", attempt=expected_attempt))
        if entry.get("replacement_route") not in allowed_routes:
            failures.append(_failure("exposure_recomposition_receipt", "Recomposition receipt has an invalid replacement route.", attempt=expected_attempt))

    if failures:
        raise ExecutionError("Exposure action plan failed validation.", failures)


def _packet_integrity_failures(packet: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    catalog_reference = packet.get("catalog_path", str(DEFAULT_CATALOG))
    catalog_path = Path(catalog_reference)
    if not catalog_path.is_absolute():
        catalog_path = ROOT / catalog_path
    try:
        catalog = load_catalog(catalog_path)
        if packet.get("catalog_hash") != digest(canonical_json(catalog)):
            failures.append(_failure("catalog_hash_stale", "Execution packet was compiled from an outdated catalog."))
    except (ExecutionError, OSError) as error:
        failures.append(_failure("catalog_unavailable", "Execution packet catalog cannot be validated.", detail=str(error)))
    for item in packet.get("compiled_context", []):
        for source in item.get("sources", []):
            try:
                path = resolve_project_path(source["path"])
                if digest(path.read_bytes()) != source.get("source_hash"):
                    failures.append(_failure("source_hash_stale", "Execution packet source changed after compilation.", path=source["path"]))
                if digest(source.get("content_yaml", "")) != source.get("context_hash"):
                    failures.append(_failure("context_hash_invalid", "Compiled leaf content hash is invalid.", path=source["path"]))
            except (ExecutionError, OSError) as error:
                failures.append(_failure("source_unavailable", "Execution packet source cannot be validated.", path=source.get("path"), detail=str(error)))
    for reference in packet.get("deferred_references", []):
        try:
            path = resolve_project_path(reference["path"])
            if digest(path.read_bytes()) != reference.get("source_hash"):
                failures.append(_failure("reference_hash_stale", "Deferred reference source changed after compilation.", reference_id=reference.get("reference_id"), path=reference["path"]))
        except (ExecutionError, OSError) as error:
            failures.append(_failure("reference_unavailable", "Deferred reference cannot be validated.", reference_id=reference.get("reference_id"), detail=str(error)))
    return failures


def _reference_access_failures(packet: dict[str, Any], record: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    access = record.get("reference_access")
    if not isinstance(access, list):
        return [_failure("reference_access_schema", "reference_access must be a list.")]
    expected = {
        reference["reference_id"]: reference
        for reference in packet.get("deferred_references", [])
        if _reference_is_active(reference, packet.get("features", []))
    }
    received: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in access:
        if not isinstance(receipt, dict) or not isinstance(receipt.get("reference_id"), str):
            failures.append(_failure("reference_access_schema", "Each reference access receipt needs a reference_id."))
            continue
        reference_id = receipt["reference_id"]
        reference = expected.get(reference_id)
        if reference is None:
            failures.append(_failure("reference_access_unexpected", "Reference was accessed without packet activation.", reference_id=reference_id))
            continue
        received[reference_id].append(receipt)
        expected_phase = reference["materialize_at_phase"]
        if receipt.get("phase_id") != expected_phase:
            failures.append(_failure("reference_access_phase", "Reference was materialized at the wrong phase.", reference_id=reference_id, expected=expected_phase, actual=receipt.get("phase_id")))
        if receipt.get("status") != "loaded":
            failures.append(_failure("reference_access_status", "Reference access receipt must record loaded status.", reference_id=reference_id, actual=receipt.get("status")))
        for field in ("path", "source_hash", "context_hash"):
            if receipt.get(field) != reference.get(field):
                failures.append(_failure("reference_access_hash", "Reference access receipt does not match packet provenance.", reference_id=reference_id, field=field, expected=reference.get(field), actual=receipt.get(field)))
    for reference_id in expected:
        if not received.get(reference_id):
            failures.append(_failure("reference_access_missing", "Required deferred source was not materialized.", reference_id=reference_id))
        elif len(received[reference_id]) != 1:
            failures.append(_failure("reference_access_duplicate", "Deferred source must have exactly one access receipt.", reference_id=reference_id, count=len(received[reference_id])))
    return failures


def _geometry_result_receipt_failures(receipt: Any, result: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(receipt, dict):
        return [_failure("exposure_geometry_result_missing", "Execution record must retain the deterministic geometry result.")]
    failures: list[dict[str, Any]] = []
    for field in ("valid", "required", "checks", "failure_taxonomy"):
        if receipt.get(field) != result.get(field):
            failures.append(_failure("exposure_geometry_result_mismatch", "Execution geometry result does not match deterministic validation.", field=field, expected=result.get(field), actual=receipt.get(field)))
    return failures


def _semantic_visibility_result_receipt_failures(receipt: Any, result: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(receipt, dict):
        return [_failure("semantic_visibility_result_missing", "Execution record must retain the deterministic semantic visibility result.")]
    failures: list[dict[str, Any]] = []
    for field in ("valid", "required", "checks", "failure_taxonomy"):
        if receipt.get(field) != result.get(field):
            failures.append(_failure("semantic_visibility_result_mismatch", "Execution semantic visibility result does not match deterministic validation.", field=field, expected=result.get(field), actual=receipt.get(field)))
    return failures


def validate_execution_record(packet: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    failures = _packet_integrity_failures(packet)
    failures.extend(_reference_access_failures(packet, record))
    if record.get("packet_id") != packet.get("packet_id"):
        failures.append(_failure("packet_id_mismatch", "Execution record packet_id does not match packet."))
    if record.get("packet_hash") != packet.get("packet_hash"):
        failures.append(_failure("packet_hash_mismatch", "Execution record packet_hash does not match packet."))

    expected_phases = [phase["id"] for phase in packet["phases"]]
    actual_phases = record.get("phases")
    if not isinstance(actual_phases, list) or [item.get("id") for item in actual_phases] != expected_phases:
        failures.append(_failure("phase_order", "Execution record must contain every phase in pipeline order.", expected=expected_phases))
        actual_by_id: dict[str, dict[str, Any]] = {}
    else:
        actual_by_id = {item["id"]: item for item in actual_phases}
        for phase in packet["phases"]:
            actual = actual_by_id[phase["id"]]
            if actual.get("status") != "complete":
                failures.append(_failure("phase_incomplete", "Required phase is not complete.", phase=phase["id"]))
            applied = set(actual.get("applied_nodes", []))
            unexpected_nodes = sorted(applied - set(phase["required_nodes"]))
            if unexpected_nodes:
                failures.append(_failure("phase_node_scope", "Phase applied nodes outside its compiled scope.", phase=phase["id"], unexpected_nodes=unexpected_nodes))
            missing_nodes = sorted(set(phase["required_nodes"]) - applied)
            if missing_nodes:
                failures.append(_failure("phase_node_coverage", "Phase skipped selected rule nodes.", phase=phase["id"], missing_nodes=missing_nodes))
            missing_phase_claims = sorted(set(phase["required_claims"]) - set(actual.get("claims", [])))
            if missing_phase_claims:
                failures.append(_failure("phase_claim_coverage", "Phase is missing required claims.", phase=phase["id"], missing_claims=missing_phase_claims))

    claims = set(record.get("claims", []))
    missing_claims = sorted(set(packet["required_claims"]) - claims)
    if missing_claims:
        failures.append(_failure("claim_coverage", "Execution record is missing selected rule claims.", missing_claims=missing_claims))

    selected_ids = {node["id"] for node in packet["selected_nodes"]}
    selected_phases = {node["id"]: set(node["phases"]) for node in packet["selected_nodes"]}
    provenance = record.get("provenance")
    if not isinstance(provenance, list):
        failures.append(_failure("provenance_schema", "Execution record provenance must be a list."))
        provenance = []
    provenance_by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in provenance:
        if not isinstance(entry, dict) or not isinstance(entry.get("claim"), str):
            failures.append(_failure("provenance_entry", "Every provenance entry requires claim, node_id, and phase_id."))
            continue
        if entry.get("node_id") not in selected_ids:
            failures.append(_failure("provenance_node", "Provenance references an unselected rule node.", entry=entry))
            continue
        if entry.get("phase_id") not in expected_phases:
            failures.append(_failure("provenance_phase", "Provenance references an unknown phase.", entry=entry))
            continue
        if entry["phase_id"] not in selected_phases[entry["node_id"]]:
            failures.append(_failure("provenance_phase_scope", "Provenance maps a rule node to a phase it does not execute in.", entry=entry))
            continue
        provenance_by_claim[entry["claim"]].append(entry)
    for claim in packet["required_claims"]:
        if not provenance_by_claim.get(claim):
            failures.append(_failure("provenance_coverage", "Required claim has no provenance.", claim=claim))

    validated_prompt_pack: dict[str, str] | None = None
    try:
        try:
            from scripts.export_prompt_pack import validate_prompt_pack
        except ModuleNotFoundError:  # pragma: no cover - direct script execution path
            from export_prompt_pack import validate_prompt_pack

        validated_prompt_pack = validate_prompt_pack(record.get("prompt_pack"))
    except ValueError as error:
        failures.append(_failure("prompt_pack", str(error)))

    if "visible_adult_exposure" in packet["required_claims"]:
        if validated_prompt_pack is not None:
            try:
                validate_visible_exposure_contract(record.get("exposure_contract"), validated_prompt_pack)
            except ExecutionError as error:
                failures.extend(error.failures)
        else:
            failures.append(_failure("visible_exposure_prompt_unavailable", "Visible exposure cannot be validated until the prompt pack is valid."))

    if "exposure_action_plan" in packet["required_claims"]:
        try:
            try:
                from scripts.check_exposure_geometry import check_exposure_geometry
            except ModuleNotFoundError:  # pragma: no cover - direct script execution path
                from check_exposure_geometry import check_exposure_geometry

            geometry_result = check_exposure_geometry(packet, record)
            failures.extend(_geometry_result_receipt_failures(record.get("exposure_geometry_result"), geometry_result))
            if not geometry_result["valid"]:
                failures.extend(geometry_result["failures"])
        except (ExecutionError, ValueError) as error:
            failures.append(_failure("exposure_geometry_unavailable", "Exposure geometry validator could not run.", detail=str(error)))
        try:
            try:
                from scripts.check_semantic_exposure_visibility import check_semantic_exposure_visibility
            except ModuleNotFoundError:  # pragma: no cover - direct script execution path
                from check_semantic_exposure_visibility import check_semantic_exposure_visibility

            semantic_result = check_semantic_exposure_visibility(packet, record)
            failures.extend(_semantic_visibility_result_receipt_failures(record.get("semantic_exposure_visibility_result"), semantic_result))
            if not semantic_result["valid"]:
                failures.extend(semantic_result["failures"])
        except (ExecutionError, ValueError) as error:
            failures.append(_failure("semantic_visibility_unavailable", "Semantic exposure visibility validator could not run.", detail=str(error)))
        if validated_prompt_pack is not None:
            try:
                validate_exposure_action_plan(
                    record.get("exposure_action_plan"),
                    record.get("exposure_contract"),
                    record.get("exposure_feasibility_review"),
                    record.get("recomposition_attempts"),
                    validated_prompt_pack,
                )
            except ExecutionError as error:
                failures.extend(error.failures)
        else:
            failures.append(_failure("exposure_action_prompt_unavailable", "Exposure action cannot be validated until the prompt pack is valid."))

    if failures:
        raise ExecutionError("Execution record failed validation.", failures)
    return {
        "valid": True,
        "packet_id": packet["packet_id"],
        "prompt_pack": record["prompt_pack"],
        "metrics": packet["metrics"],
    }


def quality_contract(path: Path = DEFAULT_QUALITY_CONTRACT) -> dict[str, Any]:
    contract = load_yaml(path)
    if contract.get("schema_version") != "1.0.0":
        raise ExecutionError("Unsupported quality contract schema version.")
    return contract


def _semantic_source_keys(packet: dict[str, Any]) -> set[tuple[str, tuple[str, ...], str]]:
    sources = [source for item in packet.get("compiled_context", []) for source in item.get("sources", [])]
    sources.extend(reference for reference in packet.get("deferred_references", []) if _reference_is_active(reference, packet.get("features", [])))
    return {
        (str(source.get("path")), tuple(source.get("sections", [])), str(source.get("context_hash")))
        for source in sources
    }


def validate_quality_gate(
    legacy_packet: dict[str, Any],
    candidate_packet: dict[str, Any],
    benchmark: dict[str, Any],
    contract_path: Path = DEFAULT_QUALITY_CONTRACT,
) -> dict[str, Any]:
    contract = quality_contract(contract_path)
    failures: list[dict[str, Any]] = []
    missing_claims = sorted(set(legacy_packet.get("required_claims", [])) - set(candidate_packet.get("required_claims", [])))
    if missing_claims:
        failures.append(_failure("quality_claim_regression", "Candidate packet dropped legacy required claims.", missing_claims=missing_claims))
    reduction = float(candidate_packet.get("metrics", {}).get("context_reduction_percent", 0))
    minimum_reduction = float(contract["performance"]["minimum_context_reduction_percent"])
    if reduction < minimum_reduction:
        failures.append(_failure("performance_target", "Candidate packet misses required context reduction.", actual=reduction, minimum=minimum_reduction))
    initial_reduction = float(candidate_packet.get("metrics", {}).get("initial_context_reduction_percent", 0))
    minimum_initial_reduction = float(contract["performance"].get("minimum_initial_context_reduction_percent", 0))
    if initial_reduction < minimum_initial_reduction:
        failures.append(_failure("initial_performance_target", "Candidate packet misses required initial-load reduction.", actual=initial_reduction, minimum=minimum_initial_reduction))
    missing_semantic_sources = _semantic_source_keys(legacy_packet) - _semantic_source_keys(candidate_packet)
    if missing_semantic_sources:
        failures.append(_failure("quality_source_coverage", "Candidate packet dropped a required source section from its complete semantic closure.", missing_sources=sorted(missing_semantic_sources)))

    baseline_scores = benchmark.get("baseline_scores", {}) if isinstance(benchmark, dict) else {}
    candidate_scores = benchmark.get("candidate_scores", {}) if isinstance(benchmark, dict) else {}
    for category in contract["benchmark"]["existing_categories"]:
        if category not in baseline_scores or category not in candidate_scores:
            failures.append(_failure("benchmark_missing", "Benchmark category is missing.", category=category))
        elif candidate_scores[category] < baseline_scores[category]:
            failures.append(_failure("benchmark_regression", "Candidate score is lower than baseline.", category=category, baseline=baseline_scores[category], candidate=candidate_scores[category]))
    for category in contract["benchmark"]["new_categories"]:
        if category not in candidate_scores:
            failures.append(_failure("benchmark_missing", "New benchmark category is missing.", category=category))
        elif candidate_scores[category] < contract["benchmark"]["minimum_new_category_score"]:
            failures.append(_failure("benchmark_minimum", "New benchmark category is below the quality floor.", category=category, candidate=candidate_scores[category]))
    candidate_claims = set(candidate_packet.get("required_claims", []))
    hard_gate_results = benchmark.get("hard_gates", {}) if isinstance(benchmark, dict) else {}
    for gate_id, gate in contract["benchmark"].get("hard_gates", {}).items():
        if gate["applies_when_required_claim"] not in candidate_claims:
            continue
        if hard_gate_results.get(gate_id) != gate["required_value"]:
            failures.append(
                _failure(
                    "benchmark_hard_gate",
                    "Benchmark failed a mandatory quality gate.",
                    gate=gate_id,
                    expected=gate["required_value"],
                    actual=hard_gate_results.get(gate_id),
                )
            )
    if failures:
        raise ExecutionError("Quality gate failed.", failures)
    return {"valid": True, "context_reduction_percent": reduction, "initial_context_reduction_percent": initial_reduction, "quality_non_regression": True}


def request_payload(value: Any) -> tuple[str, list[str]]:
    if isinstance(value, str):
        return value, []
    if not isinstance(value, dict):
        raise ExecutionError("Request input must be a string or JSON object.")
    request = value.get("request")
    features = value.get("features", [])
    if not isinstance(features, list) or not all(isinstance(item, str) for item in features):
        raise ExecutionError("Request features must be a list of strings.")
    return request, features
