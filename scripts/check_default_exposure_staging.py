#!/usr/bin/env python3
"""Validate exposure-first default pose and wardrobe staging."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "nsfw-default-exposure-staging.yaml"


def _failure(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def _load_policy() -> dict[str, Any]:
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or policy.get("schema_version") != "1.0.0" or policy.get("name") != "nsfw-default-exposure-staging":
        raise ValueError("Unsupported default exposure staging policy.")
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


def _contains_any(value: str, terms: Iterable[str]) -> bool:
    return any(term.casefold() in value for term in terms)


def _target_terms(target: Any) -> tuple[str, ...]:
    if not isinstance(target, str):
        return ()
    if target == "vulva":
        return ("vulva", "pussy")
    return (target,)


def _target_position(prompt: str, target: str) -> int:
    positions = [prompt.find(term) for term in _target_terms(target)]
    positions = [position for position in positions if position >= 0]
    return min(positions) if positions else -1


def _has_lower_body_failure_receipt(record: dict[str, Any]) -> bool:
    receipts = record.get("recomposition_attempts")
    if not isinstance(receipts, list):
        return False
    markers = ("vulva_route_failed", "lower_body_route_failed", "lower_body_semantic_failed", "lower_body_geometry_failed")
    for receipt in receipts:
        if not isinstance(receipt, dict):
            continue
        reasons = receipt.get("failure_reasons")
        if isinstance(reasons, list) and any(isinstance(reason, str) and any(marker in reason for marker in markers) for reason in reasons):
            return True
    return False


def _wardrobe_prompt_terms(wardrobe_mode: str, action_id: str) -> tuple[str, ...]:
    if wardrobe_mode == "direct_bare_no_wardrobe":
        return ("nude", "bare")
    if "lower_body" in wardrobe_mode or "lower" in action_id or "panties" in action_id:
        return ("lower garment", "panties", "fabric")
    if "upper_body" in wardrobe_mode or "upper" in action_id or "shirt" in action_id:
        return ("upper garment", "shirt", "fabric")
    return ("garment", "fabric")


def check_default_exposure_staging(packet: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    if "default_exposure_staging_plan" not in packet.get("required_claims", []):
        return {"valid": True, "required": False, "checks": {}, "failures": [], "failure_taxonomy": []}

    policy = _load_policy()
    schema = policy["default_exposure_staging_plan"]
    failures: list[dict[str, Any]] = []
    checks: dict[str, bool] = {}

    plan = record.get("default_exposure_staging_plan")
    if not isinstance(plan, dict):
        return {
            "valid": False,
            "required": True,
            "checks": {},
            "failures": [_failure("default_exposure_staging_plan_missing", "Eligible adult exposure scene is missing default_exposure_staging_plan.")],
            "failure_taxonomy": ["default_exposure_staging_plan_missing"],
        }

    missing_fields = [field for field in schema["required_fields"] if field not in plan]
    if missing_fields:
        failures.append(_failure("default_exposure_staging_missing_fields", "Default exposure staging plan is incomplete.", missing_fields=missing_fields))

    default_reason = plan.get("default_reason")
    target_priority = plan.get("target_priority")
    pose_template_id = plan.get("pose_template_id")
    pose_family = plan.get("pose_family")
    wardrobe_mode = plan.get("wardrobe_mode")
    exposure_route = plan.get("exposure_route")
    action_id = plan.get("action_id")
    camera_proof = plan.get("camera_proof")
    semantic_guards = plan.get("semantic_clearance_guards")

    if default_reason not in schema["default_reasons"]:
        failures.append(_failure("default_exposure_staging_reason", "Default exposure staging reason is invalid.", actual=default_reason))
    if pose_family not in schema["pose_families"]:
        failures.append(_failure("default_exposure_staging_pose_family", "Default exposure staging pose family is invalid.", actual=pose_family))
    if wardrobe_mode not in schema["wardrobe_modes"]:
        failures.append(_failure("default_exposure_staging_wardrobe_mode", "Default exposure staging wardrobe mode is invalid.", actual=wardrobe_mode))

    if not isinstance(target_priority, list) or not target_priority or not all(isinstance(item, str) and item for item in target_priority):
        failures.append(_failure("default_exposure_staging_target_priority", "target_priority must be a non-empty list of targets."))
        target_priority = []
    if not isinstance(camera_proof, list) or not all(isinstance(item, str) and item for item in camera_proof):
        failures.append(_failure("default_exposure_staging_camera_proof", "camera_proof must be a list of strings."))
        camera_proof = []
    if not isinstance(semantic_guards, list) or not semantic_guards or not all(isinstance(item, str) and item.strip() for item in semantic_guards):
        failures.append(_failure("default_exposure_staging_semantic_guards", "semantic_clearance_guards must be a non-empty list of strings."))
        semantic_guards = []

    exposure_contract = record.get("exposure_contract") if isinstance(record.get("exposure_contract"), dict) else {}
    exposure_action = record.get("exposure_action_plan") if isinstance(record.get("exposure_action_plan"), dict) else {}
    semantic_plan = record.get("semantic_exposure_visibility_plan") if isinstance(record.get("semantic_exposure_visibility_plan"), dict) else {}
    geometry_plan = record.get("exposure_geometry_plan") if isinstance(record.get("exposure_geometry_plan"), dict) else {}
    active_target = exposure_action.get("primary_target") or exposure_contract.get("evidence_target")
    subject = exposure_contract.get("subject_presentation")

    if active_target not in target_priority:
        failures.append(_failure("default_exposure_staging_target_mismatch", "Active exposure target must be present in staging target_priority.", active_target=active_target, target_priority=target_priority))

    missing_intent_reasons = {"unspecified_wardrobe_and_pose", "wardrobe_specified_pose_unspecified", "pose_specified_wardrobe_unspecified"}
    if subject == "female_feminine" and default_reason in missing_intent_reasons:
        vulva_first = bool(target_priority) and target_priority[0] == "vulva"
        fallback_receipt = active_target == "nipple" and _has_lower_body_failure_receipt(record)
        checks["female_default_vulva_first_or_recorded_fallback"] = vulva_first or fallback_receipt
        if not (vulva_first or fallback_receipt):
            failures.append(_failure("default_exposure_staging_vulva_priority", "Female/feminine missing pose or wardrobe defaults must try vulva first, or record a lower-body route failure before nipple fallback."))

    action_matches = exposure_route == exposure_action.get("route") and action_id == exposure_action.get("action")
    checks["matches_exposure_action_plan"] = action_matches
    if not action_matches:
        failures.append(
            _failure(
                "default_exposure_staging_action_mismatch",
                "Staging exposure route and action_id must match exposure_action_plan.",
                staging_route=exposure_route,
                action_route=exposure_action.get("route"),
                staging_action=action_id,
                action=exposure_action.get("action"),
            )
        )

    mode_definition = schema["wardrobe_modes"].get(wardrobe_mode, {}) if isinstance(wardrobe_mode, str) else {}
    if mode_definition:
        allowed_route = mode_definition.get("exposure_route")
        allowed_actions = set(mode_definition.get("action_ids", []))
        if exposure_route != allowed_route:
            failures.append(_failure("default_exposure_staging_route_mode_mismatch", "Staging wardrobe mode does not allow this exposure route.", wardrobe_mode=wardrobe_mode, expected=allowed_route, actual=exposure_route))
        if action_id not in allowed_actions:
            failures.append(_failure("default_exposure_staging_action_mode_mismatch", "Staging wardrobe mode does not allow this action.", wardrobe_mode=wardrobe_mode, action_id=action_id))

    required_camera = {"target_in_frame", "target_unoccluded", "target_on_focal_plane"}
    camera_set = set(camera_proof)
    action_camera = set(exposure_action.get("camera_proof", [])) if isinstance(exposure_action.get("camera_proof"), list) else set()
    checks["camera_proof_matches_action"] = required_camera.issubset(camera_set) and camera_set.issubset(action_camera | required_camera)
    if not checks["camera_proof_matches_action"]:
        failures.append(_failure("default_exposure_staging_camera_mismatch", "Staging camera proof must include required proof and agree with exposure_action_plan.camera_proof.", staging_camera=sorted(camera_set), action_camera=sorted(action_camera)))

    if default_reason == "wardrobe_specified_pose_unspecified" and isinstance(pose_template_id, str):
        forbidden = set(schema["routing_cases"]["wardrobe_specified_pose_unspecified"]["forbidden_pose_templates"])
        if pose_template_id in forbidden or pose_template_id.startswith("ordinary_"):
            failures.append(_failure("default_exposure_staging_ordinary_pose", "Wardrobe-specified scenes without a pose cannot use an ordinary pose template.", pose_template_id=pose_template_id))

    if isinstance(pose_template_id, str) and pose_template_id in schema.get("lower_body_readable_presets", {}):
        expected_family = schema["lower_body_readable_presets"][pose_template_id]["pose_family"]
        if pose_family != expected_family:
            failures.append(_failure("default_exposure_staging_pose_family_mismatch", "Pose template family does not match staging pose_family.", pose_template_id=pose_template_id, expected=expected_family, actual=pose_family))

    semantic_target_matches = semantic_plan.get("target") == active_target
    checks["semantic_target_matches"] = semantic_target_matches
    if not semantic_target_matches:
        failures.append(_failure("default_exposure_staging_semantic_target_mismatch", "Semantic visibility target must match active staging target.", semantic_target=semantic_plan.get("target"), active_target=active_target))

    semantic_prompt_guards = [item.casefold().strip() for item in semantic_plan.get("positive_prompt_guards", [])] if isinstance(semantic_plan.get("positive_prompt_guards"), list) else []
    for guard in semantic_guards:
        if guard.casefold().strip() not in semantic_prompt_guards:
            failures.append(_failure("default_exposure_staging_semantic_guard_mismatch", "Staging semantic guard must be present in semantic_exposure_visibility_plan.positive_prompt_guards.", guard=guard))

    if isinstance(geometry_plan, dict):
        projected_point = geometry_plan.get("target", {}).get("projected_point") if isinstance(geometry_plan.get("target"), dict) else None
        checks["geometry_target_projected"] = isinstance(projected_point, list) and len(projected_point) == 2
        if not checks["geometry_target_projected"]:
            failures.append(_failure("default_exposure_staging_geometry_missing", "Staging validation requires an exposure_geometry_plan target projection."))

    positive_prompts = _positive_prompt_fields(record)
    checks["positive_prompts_present"] = bool(positive_prompts)
    if not positive_prompts:
        failures.append(_failure("default_exposure_staging_prompt_missing", "Staging requires positive prompt fields."))
    elif isinstance(active_target, str):
        pose_phrase = pose_template_id.replace("_", " ").casefold() if isinstance(pose_template_id, str) else ""
        wardrobe_terms = _wardrobe_prompt_terms(str(wardrobe_mode), str(action_id))
        camera_terms = ("in frame", "unobscured", "focal plane")
        normalized_guards = [guard.casefold().strip() for guard in semantic_guards]
        for field, prompt in positive_prompts.items():
            target_position = _target_position(prompt, active_target)
            if target_position < 0:
                failures.append(_failure("default_exposure_staging_prompt_target", "Positive prompt must name the active target or accepted target alias early.", field=field, target=active_target))
            elif target_position > 320:
                failures.append(_failure("default_exposure_staging_prompt_order", "Active target must appear in the early subject description.", field=field, target=active_target))
            if pose_phrase and pose_phrase not in prompt:
                failures.append(_failure("default_exposure_staging_prompt_pose", "Positive prompt must include the selected exposure-first pose template early.", field=field, pose_template_id=pose_template_id))
            elif pose_phrase and prompt.find(pose_phrase) > 420:
                failures.append(_failure("default_exposure_staging_prompt_order", "Pose template must appear in the early subject description.", field=field, pose_template_id=pose_template_id))
            if not _contains_any(prompt, wardrobe_terms):
                failures.append(_failure("default_exposure_staging_prompt_wardrobe", "Positive prompt must include the staging wardrobe mode or garment-action evidence.", field=field, wardrobe_mode=wardrobe_mode))
            if not all(term in prompt for term in camera_terms):
                failures.append(_failure("default_exposure_staging_prompt_camera", "Positive prompt must include ray-readable camera proof: in frame, unobscured, and focal plane.", field=field))
            missing_guards = [guard for guard in normalized_guards if guard not in prompt]
            if missing_guards:
                failures.append(_failure("default_exposure_staging_prompt_semantic", "Positive prompt must include staging semantic clearance guards.", field=field, missing_guards=missing_guards))

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
    result = check_default_exposure_staging(packet, record)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
