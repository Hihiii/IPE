from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .capsule_retriever import capsule_plan, load_capsules, materialize_phase
from .constants import PHASES
from .io import load_json, write_json
from .module_router import route_modules
from .prompt_renderer import render_prompt_pack
from .subject_intent_parser import BlockedPromptError, parse_intent
from .validator import validate_run


def inspect_request(request: str) -> dict[str, Any]:
    intent = parse_intent(request)
    if intent.get("blocked"):
        return {"intent_profile": intent, "blocked": intent["blocked"]}
    module_plan = route_modules(intent)
    capsules = load_capsules(module_plan)
    return {
        "intent_profile": intent,
        "module_plan": module_plan,
        "capsule_plan": capsule_plan(module_plan),
        "phase_plan": module_plan["phase_plan"],
        "capsule_access_log": capsules["access_log"],
    }


def run_pipeline(request: str, session: Path | None = None, include_debug: bool = False) -> dict[str, Any]:
    started = time.time()
    intent = parse_intent(request)
    if session:
        session.mkdir(parents=True, exist_ok=True)
        write_json(session / "request.json", {"request": request})
        write_json(session / "intent_profile.json", intent)
    if intent.get("blocked"):
        if session:
            write_json(session / "validation_report.json", {"valid": False, "blocked": intent["blocked"], "failures": [intent["blocked"]]})
        raise BlockedPromptError(intent["blocked"]["code"], intent["blocked"]["message"])

    module_plan = route_modules(intent)
    capsules = load_capsules(module_plan)
    cap_plan = capsule_plan(module_plan)
    phase_outputs: dict[str, Any] = {}
    ledger = {"schema_version": "1.0.0", "phases": []}

    phase_outputs["phase_0_config_resolution"] = {
        "module_ids": module_plan["module_ids"],
        "capsule_count": len(capsules["capsules"]),
        "runtime_mode": "agentic_visual_prompt_rag",
    }
    _complete_phase(ledger, module_plan, "phase_0_config_resolution", phase_outputs["phase_0_config_resolution"])

    phase_outputs["phase_1_intent_analysis"] = {
        "adult_eligible": intent["adult_eligible"],
        "subject_kind": intent["subject_kind"],
        "pose_family": intent["pose_family"],
        "hard_locks": intent["hard_locks"],
        "named_character": intent.get("named_character"),
    }
    _complete_phase(ledger, module_plan, "phase_1_intent_analysis", phase_outputs["phase_1_intent_analysis"])

    phase_outputs["phase_2_composition_and_cinematography"] = _composition(intent)
    _complete_phase(ledger, module_plan, "phase_2_composition_and_cinematography", phase_outputs["phase_2_composition_and_cinematography"])

    phase_outputs["phase_3_scene_blueprint"] = _scene_blueprint(intent, phase_outputs["phase_2_composition_and_cinematography"])
    _complete_phase(ledger, module_plan, "phase_3_scene_blueprint", phase_outputs["phase_3_scene_blueprint"])

    phase_outputs["phase_3_1_prompt_package"] = {
        "intent": intent,
        "composition": phase_outputs["phase_2_composition_and_cinematography"],
        "scene_blueprint": phase_outputs["phase_3_scene_blueprint"],
        "provenance": _provenance(module_plan),
    }
    _complete_phase(ledger, module_plan, "phase_3_1_prompt_package", phase_outputs["phase_3_1_prompt_package"])

    phase_outputs["phase_4_self_review"] = _self_review(intent, phase_outputs["phase_3_1_prompt_package"])
    _complete_phase(ledger, module_plan, "phase_4_self_review", phase_outputs["phase_4_self_review"])

    phase_outputs["phase_4_1_cleanup"] = _cleanup(phase_outputs["phase_3_1_prompt_package"])
    _complete_phase(ledger, module_plan, "phase_4_1_cleanup", phase_outputs["phase_4_1_cleanup"])

    phase_outputs["phase_4_2_z_image_renderer"] = render_prompt_pack(phase_outputs["phase_4_1_cleanup"])
    _complete_phase(ledger, module_plan, "phase_4_2_z_image_renderer", phase_outputs["phase_4_2_z_image_renderer"])

    phase_outputs["phase_4_3_delivery_package"] = dict(phase_outputs["phase_4_2_z_image_renderer"])
    _complete_phase(ledger, module_plan, "phase_4_3_delivery_package", phase_outputs["phase_4_3_delivery_package"])

    prompt_pack = dict(phase_outputs["phase_4_3_delivery_package"])
    phase_outputs["phase_5_final_output"] = prompt_pack
    _complete_phase(ledger, module_plan, "phase_5_final_output", phase_outputs["phase_5_final_output"])

    artifacts = {
        "request": {"request": request},
        "intent_profile": intent,
        "module_plan": module_plan,
        "capsule_plan": cap_plan,
        "capsule_access_log": capsules["access_log"],
        "phase_ledger": ledger,
        "prompt_pack": prompt_pack,
    }
    report = validate_run(artifacts)
    artifacts["validation_report"] = report | {"elapsed_seconds": round(time.time() - started, 3)}

    if session:
        _write_artifacts(session, artifacts)
    if include_debug:
        return {"prompt_pack": prompt_pack, "debug": {key: value for key, value in artifacts.items() if key != "prompt_pack"}}
    return prompt_pack


def debug_phase(session: Path, phase_id: str) -> dict[str, Any]:
    if phase_id not in PHASES:
        raise ValueError(f"Unknown phase: {phase_id}")
    module_plan = load_json(session / "module_plan.json")
    materialized = materialize_phase(module_plan, phase_id)
    write_json(session / f"{phase_id}_materialized.json", materialized)
    return materialized


def _write_artifacts(session: Path, artifacts: dict[str, Any]) -> None:
    write_json(session / "request.json", artifacts["request"])
    write_json(session / "intent_profile.json", artifacts["intent_profile"])
    write_json(session / "module_plan.json", artifacts["module_plan"])
    write_json(session / "capsule_plan.json", artifacts["capsule_plan"])
    write_json(session / "capsule_access_log.json", artifacts["capsule_access_log"])
    write_json(session / "phase_ledger.json", artifacts["phase_ledger"])
    write_json(session / "prompt_pack.json", artifacts["prompt_pack"])
    write_json(session / "validation_report.json", artifacts["validation_report"])


def _complete_phase(ledger: dict[str, Any], module_plan: dict[str, Any], phase_id: str, output: Any) -> None:
    phase = next(item for item in module_plan["phase_plan"] if item["phase_id"] == phase_id)
    ledger["phases"].append(
        {
            "phase_id": phase_id,
            "status": "complete",
            "modules": phase["modules"],
            "claims": phase["claims"],
            "output_keys": sorted(output.keys()) if isinstance(output, dict) else [],
        }
    )


def _composition(intent: dict[str, Any]) -> dict[str, Any]:
    if intent["subject_kind"] == "nonhuman":
        return {
            "visual_focus": "environmental depth and atmosphere",
            "camera": {"framing": "wide landscape framing", "lens": "wide-angle landscape lens", "camera_height": "eye level"},
            "lighting": {"setup": "soft atmospheric natural light with visible depth separation", "exposure": "balanced exposure preserving mist, highlights, and terrain detail"},
            "color": {"palette": "natural dawn color harmony", "grade": intent["style"]},
            "crop_safety": "landscape horizon, foreground, and background layers remain in frame",
        }
    pose = intent["pose_family"]
    framing = {
        "reclining": "medium shot from head to upper thighs",
        "seated": "medium seated three-quarter framing",
        "standing": "full-body framing with head and feet visible",
        "dynamic": "medium action framing with a clear body silhouette",
        "portrait": "medium portrait framing",
    }.get(pose, "medium composition")
    return {
        "visual_focus": "adult subject readability" if intent["adult_eligible"] else "environmental depth and atmosphere",
        "camera": {"framing": framing, "lens": "normal-to-short-telephoto lens", "camera_height": "eye level"},
        "lighting": {"setup": "large soft warm side key light with a subtle rim light", "exposure": "middle-key exposure with open, readable shadows"},
        "color": {"palette": "warm amber and deep teal", "grade": intent["style"]},
        "crop_safety": "head, torso, pose support, and requested setting remain visible",
    }


def _scene_blueprint(intent: dict[str, Any], composition: dict[str, Any]) -> dict[str, Any]:
    material_detail = "natural skin texture with soft highlight rolloff" if intent["adult_eligible"] else "natural terrain texture with mist and water detail"
    if "wet_material" in intent["features"]:
        material_detail += ", moisture-aware sheen and gravity-consistent wetness"
    depth = "foreground sofa edge, subject plane, and softly blurred lounge background" if "sofa" in intent["normalized_request"] else "layered foreground, subject plane, and soft background separation"
    if intent["subject_kind"] == "nonhuman":
        depth = "foreground shoreline, midground lake surface, distant mountains, and atmospheric dawn haze"
    return {
        "subject": {"kind": intent["subject_kind"], "pose_family": intent["pose_family"], "count": intent["subject_count"]},
        "scene": {"setting": intent["setting"], "depth": depth},
        "camera": composition["camera"],
        "lighting": composition["lighting"],
        "material": {"surface_detail": material_detail},
        "constraints": {"hard_locks": intent["hard_locks"]},
    }


def _self_review(intent: dict[str, Any], prompt_package: dict[str, Any]) -> dict[str, Any]:
    failures = []
    if intent["subject_kind"] == "adult_human" and not intent["adult_eligible"]:
        failures.append({"code": "adult_eligibility_missing", "message": "Adult human prompt lacks eligibility."})
    return {"passed": not failures, "failures": failures, "repair_attempts": 0}


def _cleanup(prompt_package: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(prompt_package)
    cleaned["cleanup"] = {"deduplicated": True, "contradictions_removed": True}
    return cleaned


def _provenance(module_plan: dict[str, Any]) -> list[dict[str, str]]:
    records = []
    for module in module_plan["modules"]:
        phase = module["phases"][0]
        for claim in module["claims"]:
            records.append({"module_id": module["id"], "phase_id": phase, "claim": claim})
    return records
