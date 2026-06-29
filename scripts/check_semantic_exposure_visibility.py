#!/usr/bin/env python3
"""Validate positive-only semantic exposure visibility.

The geometry validator proves a recorded camera ray is feasible. This validator
checks the prompt-facing semantics that can still cause a model to cover the
selected target with hair, hands, garment folds, atmosphere, light, focus, or
crop choices.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "nsfw-semantic-exposure-visibility.yaml"

RISK_PHRASES = (
    "hair covering",
    "hair falling over",
    "hair across the chest",
    "hand covering",
    "hand over the target",
    "hand between camera and target",
    "fingers hiding",
    "fold covering",
    "sheet over the target",
    "strap across the target",
    "intact opaque",
    "steam hiding",
    "deep shadow over the target",
    "foreground blur across the target",
    "shallow focus losing the target",
    "cropped target",
)


def _failure(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def _load_policy() -> dict[str, Any]:
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or policy.get("schema_version") != "1.0.0":
        raise ValueError("Unsupported semantic exposure visibility policy.")
    return policy


def _positive_prompt_fields(record: dict[str, Any]) -> dict[str, str]:
    prompt_pack = record.get("prompt_pack")
    if not isinstance(prompt_pack, dict):
        return {}
    return {
        field: value.casefold()
        for field, value in prompt_pack.items()
        if field.endswith("_positive_prompt") and isinstance(value, str)
    }


def check_semantic_exposure_visibility(packet: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    if "semantic_exposure_visibility_plan" not in packet.get("required_claims", []):
        return {"valid": True, "required": False, "checks": {}, "failures": [], "failure_taxonomy": []}

    policy = _load_policy()
    schema = policy["semantic_exposure_visibility_plan"]
    required_fields = schema["required_fields"]
    allowed_statuses = set(schema["allowed_statuses"])
    failures: list[dict[str, Any]] = []
    checks: dict[str, bool] = {}

    plan = record.get("semantic_exposure_visibility_plan")
    if not isinstance(plan, dict):
        return {
            "valid": False,
            "required": True,
            "checks": {},
            "failures": [_failure("semantic_visibility_plan_missing", "Eligible adult exposure scene is missing semantic_exposure_visibility_plan.")],
            "failure_taxonomy": ["semantic_visibility_plan_missing"],
        }

    missing_fields = [field for field in required_fields if field not in plan]
    if missing_fields:
        failures.append(_failure("semantic_visibility_plan_missing_fields", "Semantic visibility plan is incomplete.", missing_fields=missing_fields))

    target = plan.get("target")
    exposure_contract = record.get("exposure_contract") if isinstance(record.get("exposure_contract"), dict) else {}
    exposure_action = record.get("exposure_action_plan") if isinstance(record.get("exposure_action_plan"), dict) else {}
    target_matches = target == exposure_contract.get("evidence_target") == exposure_action.get("primary_target")
    checks["target_matches_exposure_contract"] = target_matches
    if not target_matches:
        failures.append(
            _failure(
                "semantic_visibility_target_mismatch",
                "Semantic visibility target must match exposure contract and action target.",
                semantic_target=target,
                contract_target=exposure_contract.get("evidence_target"),
                action_target=exposure_action.get("primary_target"),
            )
        )

    clearance_fields = (
        "target_readability",
        "hair_clearance",
        "hand_clearance",
        "garment_edge_clearance",
        "atmosphere_light_focus_clearance",
    )
    for field in clearance_fields:
        status = plan.get(field)
        passed = isinstance(status, str) and status in allowed_statuses
        checks[field] = passed
        if not passed:
            failures.append(_failure("semantic_visibility_status", "Semantic clearance field has an invalid status.", field=field, actual=status, allowed=sorted(allowed_statuses)))

    positive_prompts = _positive_prompt_fields(record)
    checks["positive_prompts_present"] = bool(positive_prompts)
    if not positive_prompts:
        failures.append(_failure("semantic_visibility_prompt_missing", "Semantic visibility requires positive prompt fields."))

    guards = plan.get("positive_prompt_guards")
    if not isinstance(guards, list) or not guards or not all(isinstance(item, str) and item.strip() for item in guards):
        failures.append(_failure("semantic_visibility_guard_schema", "positive_prompt_guards must be a non-empty list of strings."))
        guards = []
    else:
        normalized_guards = [guard.casefold().strip() for guard in guards]
        for field, prompt in positive_prompts.items():
            missing = [guard for guard in normalized_guards if guard not in prompt]
            if missing:
                failures.append(_failure("semantic_visibility_guard_missing", "Positive prompt is missing semantic clearance guard text.", field=field, missing_guards=missing))

    for field, prompt in positive_prompts.items():
        risk_hits = [phrase for phrase in RISK_PHRASES if phrase in prompt]
        if risk_hits:
            failures.append(_failure("semantic_visibility_risk_phrase", "Positive prompt contains semantic occlusion risk language.", field=field, risk_phrases=risk_hits))

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
    result = check_semantic_exposure_visibility(packet, record)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
