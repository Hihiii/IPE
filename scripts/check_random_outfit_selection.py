#!/usr/bin/env python3
"""Validate deterministic random outfit selection for generic unspecified wardrobe."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "nsfw-random-outfit-selection.yaml"
CATALOG_PATH = ROOT / "config" / "character-identity" / "sexy-outfit-catalog.yaml"


def _failure(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML object.")
    return data


def _load_policy() -> dict[str, Any]:
    policy = _load_yaml(POLICY_PATH)
    if policy.get("schema_version") != "1.0.0" or policy.get("name") != "nsfw-random-outfit-selection":
        raise ValueError("Unsupported random outfit selection policy.")
    return policy


def _outfits() -> list[dict[str, Any]]:
    catalog = _load_yaml(CATALOG_PATH)
    outfits = catalog.get("sexy_outfit_catalog", {}).get("outfits")
    if not isinstance(outfits, list) or not outfits:
        raise ValueError("sexy-outfit-catalog.yaml must define non-empty outfits.")
    return outfits


def explicit_nude_requested(packet: dict[str, Any], policy: dict[str, Any] | None = None) -> bool:
    policy = policy or _load_policy()
    request = str(packet.get("request", "")).casefold()
    markers = policy["random_outfit_selection_plan"]["explicit_nude_request_markers"]
    return any(str(marker).casefold() in request for marker in markers)


def selected_outfit_for_packet(packet: dict[str, Any]) -> dict[str, Any]:
    outfits = _outfits()
    request = str(packet.get("request", "")).strip()
    seed = hashlib.sha256(request.encode("utf-8")).hexdigest()
    selected = dict(outfits[int(seed, 16) % len(outfits)])
    selected["selection_seed"] = seed
    return selected


def _positive_prompt_fields(record: dict[str, Any]) -> dict[str, str]:
    prompt_pack = record.get("prompt_pack")
    if not isinstance(prompt_pack, dict):
        return {}
    return {
        field: value.casefold()
        for field, value in prompt_pack.items()
        if field.endswith("_positive_prompt") and isinstance(value, str)
    }


def _required(packet: dict[str, Any], policy: dict[str, Any]) -> bool:
    features = set(packet.get("features", []))
    return {"wardrobe_unspecified", "generic_subject"}.issubset(features) and not explicit_nude_requested(packet, policy)


def check_random_outfit_selection(packet: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    policy = _load_policy()
    if not _required(packet, policy):
        return {"valid": True, "required": False, "checks": {}, "failures": [], "failure_taxonomy": []}

    schema = policy["random_outfit_selection_plan"]
    failures: list[dict[str, Any]] = []
    checks: dict[str, bool] = {}

    plan = record.get("random_outfit_selection_plan")
    if not isinstance(plan, dict):
        return {
            "valid": False,
            "required": True,
            "checks": {},
            "failures": [_failure("random_outfit_selection_plan_missing", "Generic unspecified wardrobe scene is missing random_outfit_selection_plan.")],
            "failure_taxonomy": ["random_outfit_selection_plan_missing"],
        }

    missing_fields = [field for field in schema["required_fields"] if field not in plan]
    if missing_fields:
        failures.append(_failure("random_outfit_selection_missing_fields", "Random outfit selection plan is incomplete.", missing_fields=missing_fields))

    selected = selected_outfit_for_packet(packet)
    expected = {
        "selection_method": schema["selection_method"],
        "selection_seed": selected["selection_seed"],
        "selected_outfit_id": str(selected["id"]),
        "selected_outfit_name": str(selected["name"]),
        "upper_body": str(selected["upper_body"]),
        "lower_body": str(selected["lower_body"]),
        "footwear": str(selected["footwear"]),
        "effective_wardrobe_state": "explicit_wardrobe",
        "exposure_transform_required": True,
    }
    for field, expected_value in expected.items():
        if plan.get(field) != expected_value:
            failures.append(_failure("random_outfit_selection_mismatch", "Random outfit selection field does not match deterministic selection.", field=field, expected=expected_value, actual=plan.get(field)))

    exposure_contract = record.get("exposure_contract") if isinstance(record.get("exposure_contract"), dict) else {}
    exposure_action = record.get("exposure_action_plan") if isinstance(record.get("exposure_action_plan"), dict) else {}
    if exposure_contract.get("wardrobe_state") != "explicit_wardrobe":
        failures.append(_failure("random_outfit_effective_wardrobe", "Random outfit route must be treated as explicit_wardrobe for exposure validation.", actual=exposure_contract.get("wardrobe_state")))
    if exposure_action.get("route") in schema["forbidden_routes"]:
        failures.append(_failure("random_outfit_forbidden_route", "Random outfit route cannot use direct bare no-wardrobe exposure.", route=exposure_action.get("route")))

    positive_prompts = _positive_prompt_fields(record)
    checks["positive_prompts_present"] = bool(positive_prompts)
    if not positive_prompts:
        failures.append(_failure("random_outfit_prompt_missing", "Random outfit validation requires positive prompt fields."))
    required_terms = [expected["upper_body"], expected["lower_body"], expected["footwear"]]
    for field, prompt in positive_prompts.items():
        missing_terms = [term for term in required_terms if term.casefold() not in prompt]
        if missing_terms:
            failures.append(_failure("random_outfit_prompt_terms", "Positive prompt is missing selected outfit terms.", field=field, missing_terms=missing_terms))
        first_positions = [prompt.find(term.casefold()) for term in required_terms if term.casefold() in prompt]
        if first_positions and min(first_positions) > 520:
            failures.append(_failure("random_outfit_prompt_order", "Selected outfit terms must appear in the early subject description.", field=field))

    return {
        "valid": not failures,
        "required": True,
        "checks": checks,
        "failures": failures,
        "failure_taxonomy": sorted({item["code"] for item in failures}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    record = json.loads(args.record.read_text(encoding="utf-8"))
    result = check_random_outfit_selection(packet, record)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
