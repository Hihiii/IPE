from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from ipe.capsule_retriever import materialize_phase, validate_capsules
from ipe.module_router import load_module_map, route_modules
from ipe.phase_engine import run_pipeline
from ipe.subject_intent_parser import BlockedPromptError, parse_intent
from ipe.validator import validate_session


ROOT = Path(__file__).resolve().parents[1]


def test_master_module_map_defines_twenty_capsule_systems() -> None:
    module_map = load_module_map()
    assert len(module_map["modules"]) == 20
    assert {module["id"] for module in module_map["modules"]} == {
        "subject_intent_parser",
        "human_character_system",
        "skin_rendering_system",
        "hair_physics_system",
        "emotion_expression_system",
        "pose_body_language_system",
        "wardrobe_material_system",
        "physical_coherence_system",
        "microclimate_atmosphere_system",
        "lighting_exposure_system",
        "camera_composition_system",
        "color_science_system",
        "scene_dna_system",
        "visual_narrative_system",
        "sensory_detail_system",
        "character_ip_database",
        "policy_rule_system",
        "prompt_renderer_system",
        "quality_failure_validation_system",
        "comfyui_workflow_system",
    }
    assert validate_capsules()["valid"] is True


def test_parser_routes_jpop_idol_as_eligible_adult_human() -> None:
    intent = parse_intent("25 year old jpop idol lying on sofa")
    assert intent["adult_eligible"] is True
    assert intent["subject_kind"] == "adult_human"
    assert intent["adult_age"] == 25
    assert intent["pose_family"] == "reclining"
    assert "adult_human" in intent["features"]

    plan = route_modules(intent)
    assert "human_character_system" in plan["module_ids"]
    assert "pose_body_language_system" in plan["module_ids"]
    assert "policy_rule_system" in plan["module_ids"]
    assert "prompt_renderer_system" in plan["module_ids"]


def test_parser_blocks_minor_youth_coded_and_age_ambiguous_adult_context() -> None:
    minor = parse_intent("16 year old idol explicit scene")
    assert minor["blocked"]["code"] == "minor_or_youth_coded"

    youth = parse_intent("youth-coded subject, explicit scene")
    assert youth["blocked"]["code"] == "minor_or_youth_coded"

    ambiguous = parse_intent("humanoid character explicit scene")
    assert ambiguous["blocked"]["code"] == "age_ambiguous"


def test_nonhuman_run_does_not_inject_nsfw_language() -> None:
    pack = run_pipeline("misty mountain landscape at sunrise with a lake")
    assert set(pack) == {"z_image_positive_prompt", "z_image_negative_prompt", "suggest_resolution"}
    positive = pack["z_image_positive_prompt"].casefold()
    assert "nsfw" not in positive
    assert "clearly adult" not in positive
    assert "portrait composition" not in positive
    assert "prompt detail" not in positive
    assert "wide landscape framing" in positive
    assert "1536x1024 (3:2)" == pack["suggest_resolution"]


def test_renderer_preserves_woman_subject_label() -> None:
    pack = run_pipeline("clearly adult original fictional woman, natural window-light portrait")
    positive = pack["z_image_positive_prompt"].casefold()
    assert "adult fictional woman" in positive
    assert "adult fictional man" not in positive


def test_normal_run_uses_capsules_and_phase_debug_materializes_full_yaml(tmp_path: Path) -> None:
    session = tmp_path / "session"
    pack = run_pipeline("25 year old jpop idol lying on sofa", session=session)
    positive = pack["z_image_positive_prompt"].casefold()
    assert "clearly adult" in positive
    assert "nsfw" in positive
    assert "relaxed reclining pose along a sofa" in positive
    assert "shoulders and hips supported by cushions" in positive
    assert "adult nude baseline" not in positive
    assert "readable adult presentation" not in positive
    assert "prompt detail" not in positive
    assert "adult presentation" not in pack["z_image_negative_prompt"].casefold()
    assert "extra fingers" in pack["z_image_negative_prompt"].casefold()
    access_log = json.loads((session / "capsule_access_log.json").read_text(encoding="utf-8"))
    assert access_log
    assert {entry["kind"] for entry in access_log} == {"capsule"}
    report = validate_session(session)
    assert report["valid"] is True

    module_plan = json.loads((session / "module_plan.json").read_text(encoding="utf-8"))
    materialized = materialize_phase(module_plan, "phase_2_composition_and_cinematography")
    assert materialized["sources"]
    assert {entry["kind"] for entry in materialized["access_log"]} == {"full_yaml"}


def test_blocked_run_raises_before_render() -> None:
    try:
        run_pipeline("real celebrity likeness, explicit scene")
    except BlockedPromptError as error:
        assert error.code == "real_person_blocked"
    else:  # pragma: no cover
        raise AssertionError("expected blocked prompt")


def test_ipe_cli_run_and_validate_session(tmp_path: Path) -> None:
    session = tmp_path / "cli-session"
    run = subprocess.run(
        [sys.executable, "-m", "ipe.cli", "run", "--request", "25 year old jpop idol lying on sofa", "--json", "--session", str(session)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    payload = json.loads(run.stdout)
    assert set(payload) == {"z_image_positive_prompt", "z_image_negative_prompt", "suggest_resolution"}
    assert (session / "phase_ledger.json").exists()

    validate = subprocess.run(
        [sys.executable, "-m", "ipe.cli", "validate", "--session", str(session)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr
    assert json.loads(validate.stdout)["valid"] is True


def test_ipe_benchmark_handles_render_and_reject_cases(tmp_path: Path) -> None:
    cases = {
        "cases": [
            {"id": "adult", "input": "25 year old jpop idol lying on sofa", "expected": ["adult_nude_baseline"]},
            {"id": "nonhuman", "input": "misty mountain landscape at sunrise with a lake", "expected": ["preserve_non_nsfw_input"]},
            {"id": "minor", "input": "16 year old idol explicit scene", "expected": ["reject_before_render"]},
        ]
    }
    path = tmp_path / "cases.yaml"
    path.write_text(yaml.safe_dump(cases), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "ipe.cli", "benchmark", "--cases", str(path), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["passed"] == 3
    assert report["failed"] == 0
