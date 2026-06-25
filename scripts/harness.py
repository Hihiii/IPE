#!/usr/bin/env python3
"""Deterministic, resumable Z-Image prompt-pack harness.

The harness executes the catalogued ten-phase workflow.  It writes one prompt
and checkpoint per phase, exposes resumable progress in ``_status.json``, and
only marks a session complete after the execution record validates.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import jsonschema

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import harness_checkpoint as cp
import harness_phases as auto

try:
    from scripts.execution_runtime import ExecutionError, execution_record_template, validate_execution_record
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from execution_runtime import ExecutionError, execution_record_template, validate_execution_record


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "config" / "harness-phase-schemas"
PHASE_IDS = [
    "phase_0_config_resolution",
    "phase_1_intent_analysis",
    "phase_2_composition_and_cinematography",
    "phase_3_scene_blueprint",
    "phase_3_1_prompt_package",
    "phase_4_self_review",
    "phase_4_1_cleanup",
    "phase_4_2_comfyui_renderer",
    "phase_4_3_delivery_package",
    "phase_5_final_output",
]
PHASE_DEFS = [{"id": phase_id} for phase_id in PHASE_IDS]
PHASE_LABELS = {
    "phase_0_config_resolution": "Config Resolution",
    "phase_1_intent_analysis": "Intent Analysis",
    "phase_2_composition_and_cinematography": "Cinematography",
    "phase_3_scene_blueprint": "Scene Blueprint",
    "phase_3_1_prompt_package": "Prompt Package",
    "phase_4_self_review": "Self-Review",
    "phase_4_1_cleanup": "Cleanup",
    "phase_4_2_comfyui_renderer": "Z-Image Renderer",
    "phase_4_3_delivery_package": "Delivery Package",
    "phase_5_final_output": "Final Output",
}
SCHEMA_FILENAMES = {
    "phase_0_config_resolution": "phase_0.json",
    "phase_1_intent_analysis": "phase_1.json",
    "phase_2_composition_and_cinematography": "phase_2.json",
    "phase_3_scene_blueprint": "phase_3.json",
    "phase_3_1_prompt_package": "phase_3_1.json",
    "phase_4_self_review": "phase_4.json",
    "phase_4_1_cleanup": "phase_4_1.json",
    "phase_4_2_comfyui_renderer": "phase_4_2.json",
    "phase_4_3_delivery_package": "phase_4_3.json",
    "phase_5_final_output": "phase_5.json",
}

_RESPONSE_TEMPLATES: dict[str, dict[str, Any]] = {
    "phase_1_intent_analysis": {
        "task_profile": "custom",
        "subject_type": "adult_human",
        "subject_role": "hero",
        "usage_context": "generation",
        "audience": "adult",
        "aspect_ratio": "2:3",
        "output_medium": "digital",
        "model_target": "z_image",
        "mature_content": {
            "level": "adult_explicit",
            "adult_age_lock": True,
            "style_intent": "adult NSFW cinematic prompt enhancement",
            "wardrobe_coverage": "minimal_or_nude",
            "pose_safety": "adult_allowed",
        },
        "anatomy_risk": {"level": "medium"},
        "collision_risk": {"level": "low"},
        "visual_hierarchy": ["adult subject", "cinematic composition"],
        "narrative_context": "adult cinematic scene",
        "hero_element": "clearly adult subject",
        "secondary_elements": [],
        "constraint_model": {"hard_locks": [], "soft_preferences": [], "inferred_enhancements": []},
        "risk_flags": [],
    },
    "phase_2_composition_and_cinematography": {
        "color_script": {
            "palette_type": "complementary",
            "dominant_colors": ["warm skin tones", "neutral background"],
            "saturation_strategy": "selective",
            "color_grading_intent": "cinematic natural contrast",
        },
        "lighting_intent": {
            "key_quality": "soft",
            "key_modifier": "large diffused source",
            "ratio": "medium",
            "color_temperature_strategy": "matched",
            "rim_or_separation": True,
            "background_treatment": "textured",
        },
        "lens_strategy": {
            "focal_length_category": "short_telephoto",
            "compression": "moderate",
            "aperture_intent": "medium",
            "working_distance": "moderate",
            "camera_height": "eye_level",
            "distortion_character": "natural",
        },
        "exposure_strategy": {"style": "middle_key", "contrast_ratio": "medium"},
        "composition": {
            "rule": "balanced cinematic portrait composition",
            "depth_layers": 3,
            "focal_priority": ["adult subject", "primary action", "environment"],
            "breathing_room": "comfortable",
        },
        "generator_translation": {
            "visible_lighting_effect": "soft cinematic light with readable subject detail",
            "visible_depth_effect": "layered depth with controlled background falloff",
            "visible_material_effect": "natural skin and fabric surface response",
            "visible_composition_effect": "balanced frame with clear focal priority",
        },
    },
    "phase_4_self_review": {
        "no_changes_needed": True,
    },
}


def _auto_phase_0(prior: dict[str, Any]) -> dict[str, Any]:
    packet = auto.compile_packet(prior.get("_request", ""))
    packet["phase_order"] = [phase["id"] for phase in packet["phases"]]
    return packet


def _auto_phase_3(prior: dict[str, Any]) -> dict[str, Any]:
    return auto.phase_3_scene_blueprint(
        prior.get("phase_1_intent_analysis", {}), prior.get("phase_2_composition_and_cinematography", {})
    )


def _auto_phase_3_1(prior: dict[str, Any]) -> dict[str, Any]:
    return auto.phase_3_1_prompt_package(
        prior.get("phase_1_intent_analysis", {}),
        prior.get("phase_2_composition_and_cinematography", {}),
        prior.get("phase_3_scene_blueprint", {}),
        prior.get("phase_0_config_resolution", {}),
    )


def _auto_phase_4_1(prior: dict[str, Any]) -> dict[str, Any]:
    package = prior.get("phase_3_1_prompt_package", {})
    review = prior.get("phase_4_self_review", {})
    if review and not review.get("no_changes_needed", True):
        package = review.get("optimization_pass", {}).get("optimized_prompt_package", package)
    return auto.phase_4_1_cleanup(package)


def _auto_phase_4_2(prior: dict[str, Any]) -> dict[str, Any]:
    return auto.phase_4_2_renderer(
        prior.get("phase_4_1_cleanup") or prior.get("phase_3_1_prompt_package", {}),
        prior.get("phase_0_config_resolution", {}),
        prior.get("phase_1_intent_analysis", {}),
    )


def _auto_phase_4_3(prior: dict[str, Any]) -> dict[str, Any]:
    return auto.phase_4_3_delivery(prior.get("phase_4_2_comfyui_renderer", {}))


def _auto_phase_5(prior: dict[str, Any]) -> dict[str, Any]:
    return auto.phase_5_output(prior.get("phase_4_3_delivery_package", {}), prior.get("_request", ""))


_AUTO_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "phase_0_config_resolution": _auto_phase_0,
    "phase_3_scene_blueprint": _auto_phase_3,
    "phase_3_1_prompt_package": _auto_phase_3_1,
    "phase_4_1_cleanup": _auto_phase_4_1,
    "phase_4_2_comfyui_renderer": _auto_phase_4_2,
    "phase_4_3_delivery_package": _auto_phase_4_3,
    "phase_5_final_output": _auto_phase_5,
}


def main() -> None:
    args = parse_args()
    if args.resume:
        cp.init(Path(args.resume).resolve())
    else:
        if not args.request:
            raise SystemExit("--request is required unless --resume is used.")
        workdir = Path(args.outdir).resolve() if args.outdir else Path("/tmp") / f"zimage-harness-{int(time.time())}"
        cp.init(workdir)
        cp.write_status(
            state="initializing",
            current_phase=None,
            completed_phases=[],
            phase_count=len(PHASE_IDS),
            percent_complete=0,
            waiting_for_input=False,
            started_at=time.time(),
            elapsed_seconds=0,
            next_action="compile execution packet",
            error=None,
            telemetry={"phases": {}, "cache": {"schema_hits": 0, "instruction_hits": 0}},
        )
        cp.write_request(args.request)
    resume_loop()


def resume_loop() -> None:
    while True:
        status = cp.read_status()
        next_index = _next_phase_index(status.get("completed_phases", []))
        if next_index is None:
            finalize()
            return
        execute_phase(PHASE_DEFS[next_index])


def execute_phase(phase: dict[str, str]) -> None:
    phase_id = phase["id"]
    phase_started = time.perf_counter()
    _update_progress(phase_id, state="materializing", next_action="prepare phase context")
    packet = _load_packet()
    if phase_id == "phase_0_config_resolution":
        context = {"phase_id": phase_id, "sources": [], "reference_access": []}
    else:
        if not packet:
            _fail("packet_missing", "Phase 0 packet is unavailable; cannot continue.")
        try:
            context = auto.materialize_phase(packet, phase_id)
        except Exception as error:
            _fail("materialization_failed", f"{phase_id}: {error}")

    prior = _load_prior_checkpoints(phase_id)
    instructions = _load_phase_instructions(phase_id)
    schema = _load_schema(phase_id)
    prompt_payload = {
        "phase_id": phase_id,
        "phase_label": PHASE_LABELS[phase_id],
        "materialized_context": context,
        "prior_checkpoints": prior,
        "request_schema": schema,
        "telemetry": {"materialized_sources": len(context.get("sources", []))},
    }
    response_template = _response_template(phase_id)
    if response_template is not None:
        prompt_payload["response_template"] = response_template
    if instructions:
        prompt_payload["phase_instructions"] = instructions
    cp.write_prompt(phase_id, prompt_payload)

    try:
        response = cp.read_response(phase_id)
    except json.JSONDecodeError as error:
        _fail("response_parse_failed", f"{phase_id}: {error}")
    if response is None:
        auto_handler = _AUTO_HANDLERS.get(phase_id)
        if auto_handler is None:
            _update_progress(phase_id, state="waiting_for_response", waiting_for_input=True, next_action=f"write response_{phase_id}.json")
            _emit_waiting(phase_id)
            raise SystemExit(0)
        try:
            response = auto_handler(prior)
        except Exception as error:
            _fail("auto_phase_failed", f"{phase_id}: {error}")
        cp.write_response(phase_id, response)

    if schema:
        try:
            jsonschema.validate(response, schema)
        except jsonschema.ValidationError as error:
            _fail("schema_validation_failed", _format_schema_error(phase_id, error))
    cp.clear_response(phase_id)

    if phase_id == "phase_1_intent_analysis":
        response = _apply_nsfw_outfit_logic(response, prior.get("_request", ""))
    response["_execution"] = {
        "reference_access": context.get("reference_access", []),
        "elapsed_seconds": round(time.perf_counter() - phase_started, 6),
        "materialized_sources": len(context.get("sources", [])),
    }
    cp.write(phase_id, response)
    _record_telemetry(phase_id, response["_execution"])
    _update_progress(phase_id, state="phase_complete", waiting_for_input=False, next_action="advance to next phase")


@lru_cache(maxsize=None)
def _load_schema(phase_id: str) -> dict[str, Any] | None:
    path = SCHEMA_DIR / SCHEMA_FILENAMES[phase_id]
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _response_template(phase_id: str) -> dict[str, Any] | None:
    template = _RESPONSE_TEMPLATES.get(phase_id)
    return deepcopy(template) if template is not None else None


def _format_schema_error(phase_id: str, error: jsonschema.ValidationError) -> str:
    path = "$" + "".join(f"[{item}]" if isinstance(item, int) else f".{item}" for item in error.absolute_path)
    schema_path = "$" + "".join(
        f"[{item}]" if isinstance(item, int) else f".{item}" for item in error.absolute_schema_path
    )
    details = {
        "phase": phase_id,
        "path": path,
        "schema_path": schema_path,
        "message": error.message,
    }
    if error.validator == "enum":
        details["expected"] = list(error.validator_value)
        details["actual"] = error.instance
    elif error.validator == "required":
        present = sorted(error.instance) if isinstance(error.instance, dict) else []
        details["required"] = list(error.validator_value)
        details["present"] = present
    elif error.validator in {"type", "minimum", "maximum", "minItems", "minLength"}:
        details["expected"] = error.validator_value
        details["actual"] = error.instance
    return json.dumps(details, ensure_ascii=False, sort_keys=True)


@lru_cache(maxsize=None)
def _load_phase_instructions(phase_id: str) -> str:
    filenames = {
        "phase_0_config_resolution": "skill-phase-0.yaml", "phase_1_intent_analysis": "skill-phase-1.yaml",
        "phase_2_composition_and_cinematography": "skill-phase-2.yaml", "phase_3_scene_blueprint": "skill-phase-3.yaml",
        "phase_3_1_prompt_package": "skill-phase-3-1.yaml", "phase_4_self_review": "skill-phase-4.yaml",
        "phase_4_1_cleanup": "skill-phase-4-1.yaml", "phase_4_2_comfyui_renderer": "skill-phase-4-2.yaml",
        "phase_4_3_delivery_package": "skill-phase-4-3.yaml", "phase_5_final_output": "skill-phase-5.yaml",
    }
    path = ROOT / "config" / filenames[phase_id]
    try:
        import yaml
        return str(yaml.safe_load(path.read_text(encoding="utf-8")).get("skill_phase", {}).get("instructions", ""))
    except Exception as error:
        _fail("phase_instruction_load_failed", f"{phase_id}: {error}")
    return ""  # unreachable; satisfies static type checkers


def _load_packet() -> dict[str, Any]:
    checkpoint = cp.read("phase_0_config_resolution")
    if not checkpoint:
        return {}
    data = checkpoint.get("data", {})
    return data.get("packet", data) if isinstance(data, dict) else {}


def _load_prior_checkpoints(current_phase: str) -> dict[str, Any]:
    prior: dict[str, Any] = {}
    prior["_request"] = cp.read_request()
    for phase_id in PHASE_IDS:
        if phase_id == current_phase:
            break
        checkpoint = cp.read(phase_id)
        if checkpoint:
            prior[phase_id] = checkpoint.get("data", {})
    return prior


def _next_phase_index(completed: list[str]) -> int | None:
    return next((index for index, phase_id in enumerate(PHASE_IDS) if phase_id not in completed), None)


def _apply_nsfw_outfit_logic(response: dict[str, Any], request: str) -> dict[str, Any]:
    result = dict(response)
    if auto.has_nude_trigger(request):
        result["_wardrobe_resolution"] = "full_nude"
        return result
    variant = auto.select_outfit_variant(request)
    if variant:
        result.update({"_wardrobe_resolution": "auto_outfit", "_selected_variant": variant["label"], "_outfit_anchors": variant["anchors"]})
    return result


def _execution_record(packet: dict[str, Any]) -> dict[str, Any]:
    record = execution_record_template(packet)
    completed = set(cp.read_status().get("completed_phases", []))
    all_data: dict[str, dict[str, Any]] = {}
    for phase in packet["phases"]:
        phase_id = phase["id"]
        checkpoint = cp.read(phase_id)
        data = checkpoint.get("data", {}) if checkpoint else {}
        all_data[phase_id] = data
        target = next(item for item in record["phases"] if item["id"] == phase_id)
        if phase_id in completed:
            target.update({"status": "complete", "applied_nodes": phase["required_nodes"], "claims": phase["required_claims"], "outputs": ["checkpoint"]})
            record["reference_access"].extend(data.get("_execution", {}).get("reference_access", []))

    record["claims"] = list(packet["required_claims"])
    for claim in packet["required_claims"]:
        node = next(node for node in packet["selected_nodes"] if claim in node["claims"])
        record["provenance"].append({"claim": claim, "node_id": node["id"], "phase_id": node["phases"][0]})

    def first_value(*keys: str) -> Any:
        for data in all_data.values():
            for key in keys:
                if data.get(key) is not None:
                    return data[key]
        return None

    record["exposure_contract"] = first_value("exposure_contract", "visible_exposure_contract")
    record["exposure_action_plan"] = first_value("exposure_action_plan")
    record["exposure_geometry_plan"] = first_value("exposure_geometry_plan")
    record["exposure_geometry_result"] = first_value("exposure_geometry_result")
    record["exposure_feasibility_review"] = first_value("exposure_feasibility_review")
    record["recomposition_attempts"] = first_value("recomposition_attempts") or []
    record["prompt_pack"] = {
        key: value for key, value in all_data.get("phase_5_final_output", {}).items() if not key.startswith("_")
    }
    return record


def finalize() -> None:
    packet = _load_packet()
    if not packet:
        _fail("packet_missing", "Cannot validate a session without the Phase 0 packet.")
    _update_progress("phase_5_final_output", state="validating", next_action="validate execution record")
    record = _execution_record(packet)
    cp.write_execution_record(record)
    try:
        result = validate_execution_record(packet, record)
    except ExecutionError as error:
        failure_path = cp.write_failure_trace(packet, error)
        _fail("execution_validation_failed", str(error), failure_trace=str(failure_path))
    _update_progress("phase_5_final_output", state="completed", waiting_for_input=False, next_action="none")
    print(json.dumps(result["prompt_pack"], ensure_ascii=False, indent=2))


def _record_telemetry(phase_id: str, execution: dict[str, Any]) -> None:
    status = cp.read_status()
    telemetry = status.setdefault("telemetry", {"phases": {}, "cache": {}})
    telemetry.setdefault("phases", {})[phase_id] = execution
    cp.write_status(telemetry=telemetry)


def _update_progress(phase_id: str | None, *, state: str, waiting_for_input: bool = False, next_action: str, error: str | None = None, **extra: Any) -> None:
    status = cp.read_status()
    completed = [phase for phase in status.get("completed_phases", []) if phase in PHASE_IDS]
    started = float(status.get("started_at", time.time()))
    payload = {
        "state": state, "current_phase": phase_id, "phase_count": len(PHASE_IDS),
        "phase_index": (PHASE_IDS.index(phase_id) + 1) if phase_id in PHASE_IDS else 0,
        "percent_complete": round(100 * len(completed) / len(PHASE_IDS)),
        "waiting_for_input": waiting_for_input, "elapsed_seconds": round(time.time() - started, 3),
        "next_action": next_action, "error": error,
    }
    payload.update(extra)
    cp.write_status(**payload)
    _emit_progress(cp.read_status())


def _emit_progress(status: dict[str, Any]) -> None:
    phase_id = status.get("current_phase")
    label = PHASE_LABELS.get(phase_id, "")
    if sys.stderr.isatty():
        width, percent = 20, int(status.get("percent_complete", 0))
        filled = round(width * percent / 100)
        message = f"\r[{'█' * filled}{'░' * (width - filled)}] {percent:3d}% {status.get('phase_index', 0)}/{len(PHASE_IDS)} · {label} · {status.get('state')}"
        print(message, file=sys.stderr, end="", flush=True)
    else:
        print(json.dumps({"event": "harness_progress", **status}, ensure_ascii=False), file=sys.stderr, flush=True)


def _emit_waiting(phase_id: str) -> None:
    print(f"\n[HARNESS WAITING]\nPhase: {phase_id}\nPrompt file: {cp._dir() / f'prompt_{phase_id}.json'}\nWrite response_{phase_id}.json, then run: harness.py --resume {cp._dir()}\n[/HARNESS WAITING]", file=sys.stderr)


def _fail(code: str, message: str, **details: Any) -> None:
    _update_progress(cp.read_status().get("current_phase"), state="failed", waiting_for_input=False, next_action="inspect failure trace or repair response", error=message, failure_code=code, **details)
    raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Z-Image prompt enhancement harness")
    parser.add_argument("--request", "-r", help="Original user prompt")
    parser.add_argument("--outdir", "-o", help="Session directory")
    parser.add_argument("--resume", help="Resume an existing session directory")
    return parser.parse_args()


if __name__ == "__main__":
    main()
