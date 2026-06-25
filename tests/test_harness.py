from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.harness_phases import materialize_phase, select_outfit_variant
from scripts.execution_runtime import compile_execution_packet


ROOT = Path(__file__).resolve().parents[1]


def run_harness(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/harness.py", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_materializer_uses_packet_object_without_cli_path_round_trip() -> None:
    packet = compile_execution_packet("clearly adult fictional woman in a library")
    context = materialize_phase(packet, "phase_1_intent_analysis")
    assert context["phase_id"] == "phase_1_intent_analysis"
    assert context["sources"]
    assert context["reference_access"]


def test_harness_writes_resumable_progress_and_real_materialized_context(tmp_path: Path) -> None:
    session = tmp_path / "session"
    result = run_harness("--request", "clearly adult fictional woman in a library", "--outdir", str(session))
    assert result.returncode == 0
    assert '"event": "harness_progress"' in result.stderr
    assert "[HARNESS WAITING]" in result.stderr

    status = json.loads((session / "_status.json").read_text(encoding="utf-8"))
    prompt = json.loads((session / "prompt_phase_1_intent_analysis.json").read_text(encoding="utf-8"))
    assert status["state"] == "waiting_for_response"
    assert status["phase_index"] == 2
    assert status["phase_count"] == 10
    assert status["percent_complete"] == 10
    assert status["waiting_for_input"] is True
    assert prompt["materialized_context"]["sources"]
    assert prompt["materialized_context"]["reference_access"]


def test_harness_schema_failure_is_terminal_and_visible(tmp_path: Path) -> None:
    session = tmp_path / "session"
    run_harness("--request", "clearly adult fictional woman", "--outdir", str(session))
    (session / "response_phase_1_intent_analysis.json").write_text("{}", encoding="utf-8")
    result = run_harness("--resume", str(session))
    assert result.returncode == 1
    status = json.loads((session / "_status.json").read_text(encoding="utf-8"))
    assert status["state"] == "failed"
    assert status["failure_code"] == "schema_validation_failed"
    assert not (session / "checkpoint_phase_1_intent_analysis.json").exists()


def test_auto_outfit_fallback_is_deterministic() -> None:
    prompt = "clearly adult fictional woman in a candlelit room"
    assert select_outfit_variant(prompt) == select_outfit_variant(prompt)


def test_harness_can_finalize_a_valid_nonhuman_zimage_session(tmp_path: Path) -> None:
    session = tmp_path / "session"
    run_harness("--request", "a mountain lake at dawn", "--outdir", str(session))
    phase_1 = {
        "task_profile": "landscape", "subject_type": "nonhuman", "subject_role": "environment",
        "usage_context": "generation", "audience": "general", "aspect_ratio": "3:2",
        "output_medium": "digital", "model_target": "z_image",
        "mature_content": {"level": "safe", "adult_age_lock": False, "style_intent": "cinematic", "wardrobe_coverage": "fashion_full_coverage", "pose_safety": "adult_allowed"},
        "anatomy_risk": {"level": "low"}, "collision_risk": {"level": "low"},
        "visual_hierarchy": ["lake"], "narrative_context": "dawn", "hero_element": "mountain lake at dawn",
        "secondary_elements": ["mountains"],
        "constraint_model": {"hard_locks": [], "soft_preferences": [], "inferred_enhancements": []},
        "risk_flags": [],
    }
    (session / "response_phase_1_intent_analysis.json").write_text(json.dumps(phase_1), encoding="utf-8")
    run_harness("--resume", str(session))
    phase_2 = {
        "color_script": {"palette_type": "analogous", "dominant_colors": ["blue"], "saturation_strategy": "muted", "color_grading_intent": "natural"},
        "lighting_intent": {"key_quality": "soft", "key_modifier": "sky", "ratio": "low", "color_temperature_strategy": "matched"},
        "lens_strategy": {"focal_length_category": "wide_to_normal", "compression": "low", "aperture_intent": "deep_focus", "working_distance": "far", "camera_height": "eye_level"},
        "exposure_strategy": {"style": "middle_key", "contrast_ratio": "medium"},
        "composition": {"rule": "thirds", "depth_layers": 3, "focal_priority": ["lake"], "breathing_room": "generous"},
        "generator_translation": {"visible_lighting_effect": "soft dawn light", "visible_depth_effect": "layered mountains", "visible_material_effect": "clear water", "visible_composition_effect": "wide view"},
    }
    (session / "response_phase_2_composition_and_cinematography.json").write_text(json.dumps(phase_2), encoding="utf-8")
    run_harness("--resume", str(session))
    (session / "response_phase_4_self_review.json").write_text(json.dumps({"no_changes_needed": True}), encoding="utf-8")
    result = run_harness("--resume", str(session))
    assert result.returncode == 0
    prompt_pack = json.loads(result.stdout)
    assert set(prompt_pack) == {"z_image_positive_prompt", "z_image_negative_prompt", "suggest_resolution"}
    status = json.loads((session / "_status.json").read_text(encoding="utf-8"))
    assert status["state"] == "completed"
    assert status["percent_complete"] == 100
    assert (session / "execution_record.json").exists()
