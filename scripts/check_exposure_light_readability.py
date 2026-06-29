#!/usr/bin/env python3
"""Validate target-readable cinematic exposure lighting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "nsfw-exposure-light-readability.yaml"


def _failure(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def _load_policy() -> dict[str, Any]:
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or policy.get("schema_version") != "1.0.0" or policy.get("name") != "nsfw-exposure-light-readability":
        raise ValueError("Unsupported exposure light readability policy.")
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


def _target_terms(target: Any) -> tuple[str, ...]:
    if not isinstance(target, str):
        return ()
    if target == "vulva":
        return ("vulva", "pussy")
    return (target,)


def _first_position(prompt: str, terms: tuple[str, ...]) -> int:
    positions = [prompt.find(term.casefold()) for term in terms]
    positions = [position for position in positions if position >= 0]
    return min(positions) if positions else -1


def _pose_phrase(record: dict[str, Any]) -> str:
    staging = record.get("default_exposure_staging_plan")
    if not isinstance(staging, dict) or not isinstance(staging.get("pose_template_id"), str):
        return ""
    return staging["pose_template_id"].replace("_", " ").casefold()


def _action_terms(record: dict[str, Any]) -> tuple[str, ...]:
    action = record.get("exposure_action_plan")
    if not isinstance(action, dict):
        return ()
    action_id = action.get("action")
    if not isinstance(action_id, str):
        return ()
    if action_id == "no_garment_direct_bare":
        return ("nude",)
    terms = [action_id.replace("_", " ").casefold()]
    if "pull_aside" in action_id:
        terms.append("pulling aside")
    if "pull_open" in action_id:
        terms.append("pulling open")
    if "wet_translucent" in action_id:
        terms.append("wet translucent")
    if "lower" in action_id:
        terms.append("lower garment")
    if "upper" in action_id:
        terms.append("upper garment")
    return tuple(terms)


def check_exposure_light_readability(packet: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    if "exposure_light_readability_plan" not in packet.get("required_claims", []):
        return {"valid": True, "required": False, "checks": {}, "failures": [], "failure_taxonomy": []}

    policy = _load_policy()
    schema = policy["exposure_light_readability_plan"]
    failures: list[dict[str, Any]] = []
    checks: dict[str, bool] = {}

    plan = record.get("exposure_light_readability_plan")
    if not isinstance(plan, dict):
        return {
            "valid": False,
            "required": True,
            "checks": {},
            "failures": [_failure("exposure_light_readability_plan_missing", "Eligible adult exposure scene is missing exposure_light_readability_plan.")],
            "failure_taxonomy": ["exposure_light_readability_plan_missing"],
        }

    missing_fields = [field for field in schema["required_fields"] if field not in plan]
    if missing_fields:
        failures.append(_failure("exposure_light_readability_missing_fields", "Exposure light readability plan is incomplete.", missing_fields=missing_fields))

    target = plan.get("target")
    target_zone_light_role = plan.get("target_zone_light_role")
    local_fill_strategy = plan.get("local_fill_strategy")
    shadow_floor = plan.get("shadow_floor")
    skin_midtone_policy = plan.get("skin_midtone_policy")
    contrast_separation = plan.get("contrast_separation")
    prompt_lighting_guards = plan.get("prompt_lighting_guards")
    subject_light_role = plan.get("subject_light_role")
    face_readability = plan.get("face_readability")
    body_midtone_policy = plan.get("body_midtone_policy")
    subject_shadow_floor = plan.get("subject_shadow_floor")
    background_mood_role = plan.get("background_mood_role")
    prompt_subject_lighting_guards = plan.get("prompt_subject_lighting_guards")

    exposure_contract = record.get("exposure_contract") if isinstance(record.get("exposure_contract"), dict) else {}
    exposure_action = record.get("exposure_action_plan") if isinstance(record.get("exposure_action_plan"), dict) else {}
    semantic_plan = record.get("semantic_exposure_visibility_plan") if isinstance(record.get("semantic_exposure_visibility_plan"), dict) else {}
    target_matches = target == exposure_contract.get("evidence_target") == exposure_action.get("primary_target") == semantic_plan.get("target")
    checks["target_matches_exposure_chain"] = target_matches
    if not target_matches:
        failures.append(
            _failure(
                "exposure_light_target_mismatch",
                "Light readability target must match exposure contract, action, and semantic visibility targets.",
                light_target=target,
                contract_target=exposure_contract.get("evidence_target"),
                action_target=exposure_action.get("primary_target"),
                semantic_target=semantic_plan.get("target"),
            )
        )

    if target_zone_light_role not in schema["target_zone_light_roles"]:
        failures.append(_failure("exposure_light_role", "Target-zone light role is invalid.", actual=target_zone_light_role, allowed=schema["target_zone_light_roles"]))
    if local_fill_strategy not in schema["local_fill_strategies"]:
        failures.append(_failure("exposure_light_local_fill", "Local fill strategy is invalid.", actual=local_fill_strategy, allowed=schema["local_fill_strategies"]))
    if shadow_floor not in schema["shadow_floor_allowed"]:
        failures.append(_failure("exposure_light_shadow_floor", "Target-zone shadow floor must be open or controlled_readable.", actual=shadow_floor, allowed=schema["shadow_floor_allowed"]))
    if shadow_floor in schema["shadow_floor_forbidden"]:
        failures.append(_failure("exposure_light_shadow_floor_forbidden", "Target-zone shadow floor cannot use deep shadow, black crush, or silhouette-only lighting.", actual=shadow_floor))
    if skin_midtone_policy not in schema["skin_midtone_policies"]:
        failures.append(_failure("exposure_light_skin_midtones", "Skin midtone policy is invalid.", actual=skin_midtone_policy, allowed=schema["skin_midtone_policies"]))
    if contrast_separation not in schema["contrast_separation"]["allowed"]:
        failures.append(_failure("exposure_light_contrast", "Contrast separation status is invalid.", actual=contrast_separation, allowed=schema["contrast_separation"]["allowed"]))
    if subject_light_role not in schema["subject_light_roles"]:
        failures.append(_failure("exposure_light_subject_role", "Subject light role is invalid.", actual=subject_light_role, allowed=schema["subject_light_roles"]))
    if face_readability not in schema["face_readability_allowed"]:
        failures.append(_failure("exposure_light_face_readability", "Face readability status is invalid.", actual=face_readability, allowed=schema["face_readability_allowed"]))
    if body_midtone_policy not in schema["body_midtone_policies"]:
        failures.append(_failure("exposure_light_body_midtones", "Body midtone policy is invalid.", actual=body_midtone_policy, allowed=schema["body_midtone_policies"]))
    if subject_shadow_floor not in schema["subject_shadow_floor_allowed"]:
        failures.append(_failure("exposure_light_subject_shadow_floor", "Subject shadow floor must be open or controlled_readable.", actual=subject_shadow_floor, allowed=schema["subject_shadow_floor_allowed"]))
    if subject_shadow_floor in schema["subject_shadow_floor_forbidden"]:
        failures.append(_failure("exposure_light_subject_shadow_floor_forbidden", "Subject cannot be underexposed, near-black, or black-crushed.", actual=subject_shadow_floor))
    if background_mood_role not in schema["background_mood_roles"]:
        failures.append(_failure("exposure_light_background_mood", "Background mood role is invalid.", actual=background_mood_role, allowed=schema["background_mood_roles"]))

    if not isinstance(prompt_lighting_guards, list) or not prompt_lighting_guards or not all(isinstance(item, str) and item.strip() for item in prompt_lighting_guards):
        failures.append(_failure("exposure_light_prompt_guard_schema", "prompt_lighting_guards must be a non-empty list of strings."))
        prompt_lighting_guards = []
    if not isinstance(prompt_subject_lighting_guards, list) or not prompt_subject_lighting_guards or not all(isinstance(item, str) and item.strip() for item in prompt_subject_lighting_guards):
        failures.append(_failure("exposure_light_subject_prompt_guard_schema", "prompt_subject_lighting_guards must be a non-empty list of strings."))
        prompt_subject_lighting_guards = []

    semantic_guards = [item.casefold().strip() for item in semantic_plan.get("positive_prompt_guards", [])] if isinstance(semantic_plan.get("positive_prompt_guards"), list) else []
    for guard in [*prompt_lighting_guards, *prompt_subject_lighting_guards]:
        if guard.casefold().strip() not in semantic_guards:
            failures.append(_failure("exposure_light_semantic_guard_mismatch", "Lighting guard must be present in semantic_exposure_visibility_plan.positive_prompt_guards.", guard=guard))

    positive_prompts = _positive_prompt_fields(record)
    checks["positive_prompts_present"] = bool(positive_prompts)
    if not positive_prompts:
        failures.append(_failure("exposure_light_prompt_missing", "Exposure light readability requires positive prompt fields."))

    risk_phrases = [phrase.casefold() for phrase in schema["darkness_risk_phrases"]]
    subject_risk_phrases = [phrase.casefold() for phrase in schema["subject_darkness_risk_phrases"]]
    normalized_guards = [guard.casefold().strip() for guard in [*prompt_lighting_guards, *prompt_subject_lighting_guards]]
    pose_phrase = _pose_phrase(record)
    action_terms = _action_terms(record)
    target_terms = _target_terms(target)
    for field, prompt in positive_prompts.items():
        risk_hits = [phrase for phrase in risk_phrases if phrase in prompt]
        if risk_hits:
            failures.append(_failure("exposure_light_darkness_risk_phrase", "Positive prompt contains target-darkness risk language.", field=field, risk_phrases=risk_hits))
        subject_risk_hits = [phrase for phrase in subject_risk_phrases if phrase in prompt]
        if subject_risk_hits:
            failures.append(_failure("exposure_light_subject_darkness_risk_phrase", "Positive prompt contains subject-darkness risk language.", field=field, risk_phrases=subject_risk_hits))
        target_position = _first_position(prompt, target_terms)
        if target_position < 0:
            failures.append(_failure("exposure_light_prompt_target", "Positive prompt must name the active target or accepted target alias early.", field=field, target=target))
        elif target_position > 320:
            failures.append(_failure("exposure_light_prompt_order", "Active target must appear in the early subject description.", field=field, target=target))
        if pose_phrase and pose_phrase not in prompt:
            failures.append(_failure("exposure_light_prompt_pose", "Positive prompt must include the selected exposure-first pose template.", field=field, pose_template=pose_phrase))
        if action_terms and not any(term in prompt for term in action_terms):
            failures.append(_failure("exposure_light_prompt_action", "Positive prompt must include exposure action wording.", field=field, action_terms=action_terms))
        for required in ("unobscured", "in frame", "focal plane"):
            if required not in prompt:
                failures.append(_failure("exposure_light_prompt_camera", "Positive prompt must keep target unobscured, in frame, and on the focal plane.", field=field, missing=required))
        for required in ("local fill", "open shadow detail", "readable skin midtones"):
            if required not in prompt:
                failures.append(_failure("exposure_light_prompt_readability", "Positive prompt must state target-local fill, open shadow detail, and readable skin midtones.", field=field, missing=required))
        for required in ("readable face", "soft fill across the subject", "readable body skin midtones", "open shadow detail across the body"):
            if required not in prompt:
                failures.append(_failure("exposure_light_prompt_subject_readability", "Positive prompt must state subject-level readable face, fill, body midtones, and body shadow detail.", field=field, missing=required))
        missing_guards = [guard for guard in normalized_guards if guard not in prompt]
        if missing_guards:
            failures.append(_failure("exposure_light_prompt_guard_missing", "Positive prompt is missing exposure lighting guard text.", field=field, missing_guards=missing_guards))

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
    result = check_exposure_light_readability(packet, record)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
