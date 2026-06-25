from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts.execution_runtime import (
    ExecutionError,
    compile_execution_packet,
    execution_record_template,
    load_catalog,
    materialize_phase_context,
    validate_execution_record,
    validate_quality_gate,
)
from scripts.check_exposure_geometry import check_exposure_geometry


ROOT = Path(__file__).resolve().parents[1]


def load_fixtures() -> dict:
    return yaml.safe_load((ROOT / "tests" / "execution-fixtures.yaml").read_text(encoding="utf-8"))


def complete_record(packet: dict) -> dict:
    record = execution_record_template(packet)
    for phase, expected in zip(record["phases"], packet["phases"], strict=True):
        phase["status"] = "complete"
        phase["applied_nodes"] = expected["required_nodes"]
        phase["claims"] = expected["required_claims"]
        phase["outputs"] = ["complete"]
    record["claims"] = packet["required_claims"]
    for claim in packet["required_claims"]:
        node = next(node for node in packet["selected_nodes"] if claim in node["claims"])
        phase_id = next(phase for phase in node["phases"] if phase in [item["id"] for item in packet["phases"]])
        record["provenance"].append({"claim": claim, "node_id": node["id"], "phase_id": phase_id})
    for phase in packet["phases"]:
        record["reference_access"].extend(materialize_phase_context(packet, phase["id"])["reference_access"])
    if "visible_adult_exposure" in packet["required_claims"]:
        record["exposure_contract"] = {
            "subject_presentation": "female_feminine",
            "wardrobe_state": "unspecified_wardrobe",
            "exposure_requirement": "full_nudity_required",
            "evidence_mode": "direct_bare",
            "evidence_target": "nipple",
            "garment_transformation_action": "no_garment_added",
            "camera_visibility_guard": ["evidence_target_in_frame", "evidence_target_unoccluded", "evidence_target_readable"],
            "forbidden_substitutions": ["silhouette_only", "wetness_only", "body_curve_only", "opaque_full_coverage", "cropped_or_occluded_evidence"],
        }
    if "exposure_action_plan" in packet["required_claims"]:
        record["exposure_action_plan"] = {
            "primary_target": "nipple",
            "route": "direct_bare_no_wardrobe",
            "garment_zone": "none",
            "action": "no_garment_direct_bare",
            "action_anchor": "not_applicable",
            "end_state": "nipple_visible_on_bare_skin",
            "material_cause_when_relevant": "not_applicable",
            "camera_proof": ["target_in_frame", "target_unoccluded", "target_on_focal_plane"],
            "fallback_route": "block_delivery",
        }
        record["exposure_feasibility_review"] = {
            "status": "passed",
            "attempt_count": 0,
            "target_action_compatible": "pass",
            "end_state_exposes_target": "pass",
            "camera_target_readable": "pass",
            "obstruction_free": "pass",
            "material_path_feasible": "pass",
            "surface_facing": "pass",
            "camera_ray_clear": "pass",
            "action_reach": "pass",
            "target_in_crop": "pass",
        }
        record["exposure_geometry_plan"] = {
            "coordinate_system": "camera_normalized_v1",
            "camera": {"position": [0.0, 0.0, -3.0], "forward": [0.0, 0.0, 1.0]},
            "target": {"center": [0.0, 0.0, 0.0], "surface_normal": [0.0, 0.0, -1.0], "projected_point": [0.5, 0.45]},
            "crop_bounds": {"min": [0.0, 0.0], "max": [1.0, 1.0]},
            "occluders": [],
            "garment_action": {"anchor": [0.0, 0.0, 0.0], "reach_radius": 0.0},
        }
        record["exposure_geometry_result"] = check_exposure_geometry(packet, record)
    record["prompt_pack"] = {
        "flux_final_prompt": "A clearly adult fictional nude woman with a clearly visible nipple, unobscured in the frame, in a coherent cinematic scene.",
        "z_image_positive_prompt": "clearly adult fictional nude woman, clearly visible nipple unobscured in the frame, coherent cinematic scene",
        "z_image_negative_prompt": "underage, minor, childlike, youthful appearance, fully clothed, intact opaque coverage, obscured nipple, cropped nipple",
        "suggest_resolution": "1024x1536 (2:3)",
    }
    return record


def paired_benchmark(score: int = 4) -> dict:
    contract = yaml.safe_load((ROOT / "config" / "quality-contract.yaml").read_text(encoding="utf-8"))
    baseline = {category: score for category in contract["benchmark"]["existing_categories"]}
    candidate = {category: score for category in contract["benchmark"]["existing_categories"]}
    candidate.update({category: 3 for category in contract["benchmark"]["new_categories"]})
    return {
        "baseline_scores": baseline,
        "candidate_scores": candidate,
        "hard_gates": {"visible_adult_exposure_compliance": "pass", "exposure_action_feasibility": "pass", "exposure_geometry_feasibility": "pass"},
    }


def test_catalog_covers_active_rules_and_compiles_complete_semantic_closure() -> None:
    catalog = load_catalog()
    assert catalog["mode"] == "fixed_complete_semantic_closure"
    for case in load_fixtures()["cases"]:
        packet = compile_execution_packet(case["request"])
        assert packet["packet_hash"]
        assert packet["compiled_context"]
        assert packet["metrics"]["context_reduction_percent"] >= 60
        assert all(source["source_hash"] for item in packet["compiled_context"] for source in item["sources"])
    wet_packet = compile_execution_packet(load_fixtures()["cases"][1]["request"])
    assert {"dynamic_motion_and_interaction", "material_and_environment_response", "scene_physics_and_environment"}.issubset(
        {node["id"] for node in wet_packet["selected_nodes"]}
    )
    adult_packet = compile_execution_packet("clearly adult original fictional woman, cinematic portrait")
    assert {"visible_adult_exposure", "exposure_evidence_target", "garment_transformation_action", "camera_visibility_guard", "exposure_action_plan", "exposure_action_compatibility", "exposure_geometry_plan", "exposure_feasibility_review", "exposure_recomposition"}.issubset(adult_packet["required_claims"])
    assert "visible_adult_exposure_contract" in {node["id"] for node in adult_packet["selected_nodes"]}
    assert "exposure_action_and_feasibility" in {node["id"] for node in adult_packet["selected_nodes"]}
    nonhuman_packet = compile_execution_packet("misty mountain landscape at sunrise with a lake")
    assert "visible_adult_exposure" not in nonhuman_packet["required_claims"]
    assert adult_packet["metrics"]["initial_context_reduction_percent"] >= 25
    assert all("content_yaml" not in reference for reference in adult_packet["deferred_references"])
    named_packet = compile_execution_packet("clearly adult fictional named character", ["named_character"])
    visible_paths = {source["path"] for item in named_packet["compiled_context"] for source in item["sources"]}
    visible_content = "\n".join(source.get("content_yaml", "") for item in named_packet["compiled_context"] for source in item["sources"])
    assert "config/adult-character-whitelist/index.yaml" in visible_paths
    assert "runtime-alias-resolver.json" not in visible_paths
    assert "aliases:" not in visible_content


def test_execution_validator_rejects_phase_or_provenance_skips() -> None:
    packet = compile_execution_packet("clearly adult original fictional woman, cinematic portrait")
    record = complete_record(packet)
    assert validate_execution_record(packet, record)["valid"] is True

    incomplete = deepcopy(record)
    incomplete["phases"][2]["status"] = "pending"
    with pytest.raises(ExecutionError, match="failed validation") as phase_error:
        validate_execution_record(packet, incomplete)
    assert any(failure["code"] == "phase_incomplete" for failure in phase_error.value.failures)

    missing_provenance = deepcopy(record)
    missing_provenance["provenance"] = missing_provenance["provenance"][1:]
    with pytest.raises(ExecutionError, match="failed validation") as provenance_error:
        validate_execution_record(packet, missing_provenance)
    assert any(failure["code"] == "provenance_coverage" for failure in provenance_error.value.failures)

    wrong_phase = deepcopy(record)
    wrong_phase["phases"][0]["applied_nodes"].append("adult_human_anatomy_and_pose")
    with pytest.raises(ExecutionError, match="failed validation") as scope_error:
        validate_execution_record(packet, wrong_phase)
    assert any(failure["code"] == "phase_node_scope" for failure in scope_error.value.failures)

    stale_source = deepcopy(record)
    stale_packet = deepcopy(packet)
    stale_packet["compiled_context"][0]["sources"][0]["source_hash"] = "stale"
    with pytest.raises(ExecutionError, match="failed validation") as source_error:
        validate_execution_record(stale_packet, stale_source)
    assert any(failure["code"] == "source_hash_stale" for failure in source_error.value.failures)


def test_deferred_reference_materialization_is_phase_bound_and_required() -> None:
    packet = compile_execution_packet("clearly adult original fictional woman, cinematic office portrait")
    record = complete_record(packet)
    assert record["reference_access"]
    assert validate_execution_record(packet, record)["valid"] is True

    missing = deepcopy(record)
    missing["reference_access"] = missing["reference_access"][1:]
    with pytest.raises(ExecutionError, match="failed validation") as missing_error:
        validate_execution_record(packet, missing)
    assert any(failure["code"] == "reference_access_missing" for failure in missing_error.value.failures)

    wrong_phase = deepcopy(record)
    wrong_phase["reference_access"][0]["phase_id"] = "phase_5_final_output"
    with pytest.raises(ExecutionError, match="failed validation") as phase_error:
        validate_execution_record(packet, wrong_phase)
    assert any(failure["code"] == "reference_access_phase" for failure in phase_error.value.failures)

    stale_hash = deepcopy(record)
    stale_hash["reference_access"][0]["source_hash"] = "stale"
    with pytest.raises(ExecutionError, match="failed validation") as hash_error:
        validate_execution_record(packet, stale_hash)
    assert any(failure["code"] == "reference_access_hash" for failure in hash_error.value.failures)


def test_geometry_validator_rejects_backface_occlusion_unreachable_and_crop_failures() -> None:
    packet = compile_execution_packet("clearly adult original fictional woman, cinematic portrait")
    record = complete_record(packet)
    assert validate_execution_record(packet, record)["valid"] is True

    missing_result = deepcopy(record)
    missing_result["exposure_geometry_result"] = None
    with pytest.raises(ExecutionError, match="failed validation") as missing_result_error:
        validate_execution_record(packet, missing_result)
    assert any(failure["code"] == "exposure_geometry_result_missing" for failure in missing_result_error.value.failures)

    backface = deepcopy(record)
    backface["exposure_geometry_plan"]["target"]["surface_normal"] = [0.0, 0.0, 1.0]
    backface["exposure_feasibility_review"]["surface_facing"] = "fail"
    with pytest.raises(ExecutionError, match="failed validation") as backface_error:
        validate_execution_record(packet, backface)
    assert any(failure["code"] == "geometry_surface_backfacing" for failure in backface_error.value.failures)

    occluded = deepcopy(record)
    occluded["exposure_geometry_plan"]["occluders"] = [{"id": "hand", "kind": "limb", "shape": "sphere", "center": [0.0, 0.0, -1.5], "radius": 0.2}]
    occluded["exposure_feasibility_review"]["camera_ray_clear"] = "fail"
    with pytest.raises(ExecutionError, match="failed validation") as occluded_error:
        validate_execution_record(packet, occluded)
    assert any(failure["code"] == "geometry_ray_occluded" for failure in occluded_error.value.failures)

    unreachable = deepcopy(record)
    unreachable["exposure_geometry_plan"]["garment_action"] = {"anchor": [3.0, 0.0, 0.0], "reach_radius": 0.2}
    unreachable["exposure_feasibility_review"]["action_reach"] = "fail"
    with pytest.raises(ExecutionError, match="failed validation") as reach_error:
        validate_execution_record(packet, unreachable)
    assert any(failure["code"] == "geometry_action_unreachable" for failure in reach_error.value.failures)

    cropped = deepcopy(record)
    cropped["exposure_geometry_plan"]["target"]["projected_point"] = [0.95, 0.95]
    cropped["exposure_geometry_plan"]["crop_bounds"] = {"min": [0.0, 0.0], "max": [0.8, 0.8]}
    cropped["exposure_feasibility_review"]["target_in_crop"] = "fail"
    with pytest.raises(ExecutionError, match="failed validation") as crop_error:
        validate_execution_record(packet, cropped)
    assert any(failure["code"] == "geometry_target_out_of_crop" for failure in crop_error.value.failures)


def test_visible_exposure_contract_rejects_covered_or_unverifiable_human_delivery() -> None:
    packet = compile_execution_packet("clearly adult original fictional woman in a wet white shirt")
    record = complete_record(packet)
    assert validate_execution_record(packet, record)["valid"] is True

    missing_contract = deepcopy(record)
    missing_contract["exposure_contract"] = None
    with pytest.raises(ExecutionError, match="failed validation") as missing_error:
        validate_execution_record(packet, missing_contract)
    assert any(failure["code"] == "visible_exposure_contract_missing" for failure in missing_error.value.failures)

    vague_target = deepcopy(record)
    vague_target["exposure_contract"]["evidence_target"] = "body_curve"
    with pytest.raises(ExecutionError, match="failed validation") as target_error:
        validate_execution_record(packet, vague_target)
    assert any(failure["code"] == "exposure_evidence_target" for failure in target_error.value.failures)

    covered_prompt = deepcopy(record)
    covered_prompt["prompt_pack"]["flux_final_prompt"] = "A clearly adult fictional nude woman in an intact wet white shirt, coherent cinematic lighting."
    covered_prompt["prompt_pack"]["z_image_positive_prompt"] = "clearly adult fictional nude woman, intact wet white shirt, coherent cinematic lighting"
    with pytest.raises(ExecutionError, match="failed validation") as covered_error:
        validate_execution_record(packet, covered_prompt)
    assert any(failure["code"] == "exposure_prompt_evidence" for failure in covered_error.value.failures)

    cropped_prompt = deepcopy(record)
    cropped_prompt["prompt_pack"]["flux_final_prompt"] = "A clearly adult fictional nude woman with a clearly visible nipple in a cinematic portrait."
    cropped_prompt["prompt_pack"]["z_image_positive_prompt"] = "clearly adult fictional nude woman, clearly visible nipple, cinematic portrait"
    with pytest.raises(ExecutionError, match="failed validation") as cropped_error:
        validate_execution_record(packet, cropped_prompt)
    assert any(failure["code"] == "exposure_prompt_visibility" for failure in cropped_error.value.failures)

    transformed = deepcopy(record)
    transformed["exposure_contract"].update(
        {
            "wardrobe_state": "explicit_wardrobe",
            "exposure_requirement": "partial_nudity_required",
            "garment_transformation_action": "pulled_aside",
        }
    )
    transformed["exposure_action_plan"] = {
        "primary_target": "nipple",
        "route": "direct_garment_action",
        "garment_zone": "upper_body",
        "action": "pull_open_front_panels_below_target",
        "action_anchor": "right hand grips and pulls the shirt panels apart",
        "end_state": "nipple_fully_uncovered",
        "material_cause_when_relevant": "not_applicable",
        "camera_proof": ["target_in_frame", "target_unoccluded", "target_on_focal_plane"],
        "fallback_route": "sheer_material_action",
    }
    transformed["prompt_pack"]["flux_final_prompt"] = "A clearly adult fictional woman, right hand pulling open the white shirt front panels below the nipple line, one visible nipple fully uncovered and unobscured in the frame, coherent cinematic lighting."
    transformed["prompt_pack"]["z_image_positive_prompt"] = "clearly adult fictional woman, pulling open white shirt front panels below the nipple line, visible nipple fully uncovered unobscured in the frame, coherent cinematic lighting"
    assert validate_execution_record(packet, transformed)["valid"] is True

    intact_wardrobe = deepcopy(transformed)
    intact_wardrobe["exposure_contract"]["garment_transformation_action"] = "intact_coverage"
    with pytest.raises(ExecutionError, match="failed validation") as wardrobe_error:
        validate_execution_record(packet, intact_wardrobe)
    assert any(failure["code"] == "exposure_garment_action" for failure in wardrobe_error.value.failures)

    cleavage_only = deepcopy(transformed)
    cleavage_only["prompt_pack"]["flux_final_prompt"] = "A clearly adult fictional woman in a white shirt unbuttoned at the top three buttons, visible nipple unobscured in the frame, revealing cleavage."
    cleavage_only["prompt_pack"]["z_image_positive_prompt"] = "clearly adult fictional woman, white shirt unbuttoned at the top three buttons, visible nipple unobscured in the frame, revealing cleavage"
    with pytest.raises(ExecutionError, match="failed validation") as cleavage_error:
        validate_execution_record(packet, cleavage_only)
    assert any(failure["code"] == "exposure_action_prompt_action" for failure in cleavage_error.value.failures)

    wrong_zone = deepcopy(transformed)
    wrong_zone["exposure_action_plan"]["primary_target"] = "vulva"
    with pytest.raises(ExecutionError, match="failed validation") as zone_error:
        validate_execution_record(packet, wrong_zone)
    assert any(failure["code"] in {"exposure_action_target_mismatch", "exposure_action_garment_zone", "exposure_action_incompatible"} for failure in zone_error.value.failures)

    sheer = deepcopy(transformed)
    sheer["exposure_contract"]["garment_transformation_action"] = "wet_translucent_cling"
    sheer["exposure_contract"]["evidence_mode"] = "sheer_visible_anatomy"
    sheer["exposure_action_plan"] = {
        "primary_target": "nipple",
        "route": "sheer_material_action",
        "garment_zone": "upper_body",
        "action": "wet_translucent_upper_garment",
        "action_anchor": "water-soaked fabric clings across the chest under tension",
        "end_state": "nipple_discernible_through_sheer_material",
        "material_cause_when_relevant": {
            "source_of_moisture": "a spilled glass of water",
            "fabric_state": "wet_or_translucent",
            "mechanical_condition": "clinging",
            "light_relation": "window side light reveals the wet fabric interface",
        },
        "camera_proof": ["target_in_frame", "target_unoccluded", "target_on_focal_plane"],
        "fallback_route": "direct_garment_action",
    }
    sheer["prompt_pack"]["flux_final_prompt"] = "A clearly adult fictional woman in a wet translucent clinging upper garment, a discernible nipple visible and unobscured in the frame, window side light revealing the water-soaked fabric interface."
    sheer["prompt_pack"]["z_image_positive_prompt"] = "clearly adult fictional woman, wet translucent clinging upper garment, discernible nipple visible unobscured in the frame, window side light revealing the water-soaked fabric interface"
    assert validate_execution_record(packet, sheer)["valid"] is True

    unsupported_sheer = deepcopy(sheer)
    unsupported_sheer["exposure_action_plan"]["material_cause_when_relevant"]["source_of_moisture"] = ""
    with pytest.raises(ExecutionError, match="failed validation") as sheer_error:
        validate_execution_record(packet, unsupported_sheer)
    assert any(failure["code"] == "exposure_action_material" for failure in sheer_error.value.failures)

    recomposed = deepcopy(transformed)
    recomposed["exposure_feasibility_review"]["attempt_count"] = 1
    recomposed["recomposition_attempts"] = [{"attempt": 1, "failure_reasons": ["cleavage_without_target_exposure"], "replacement_route": "direct_garment_action", "outcome": "recomposed"}]
    assert validate_execution_record(packet, recomposed)["valid"] is True

    exhausted = deepcopy(recomposed)
    exhausted["exposure_feasibility_review"]["attempt_count"] = 4
    exhausted["recomposition_attempts"] *= 4
    with pytest.raises(ExecutionError, match="failed validation") as recovery_error:
        validate_execution_record(packet, exhausted)
    assert any(failure["code"] in {"exposure_recomposition_attempt_count", "exposure_recomposition_limit"} for failure in recovery_error.value.failures)


def test_compiler_rejects_unknown_feature_hints() -> None:
    with pytest.raises(ExecutionError, match="Unknown conservative routing features"):
        compile_execution_packet("clearly adult original fictional woman", ["not_a_catalog_feature"])


def test_quality_gate_requires_coverage_performance_and_non_regression() -> None:
    packet = compile_execution_packet("clearly adult original fictional woman in a wet white shirt, dynamic pose in a steamy shower")
    assert validate_quality_gate(packet, packet, paired_benchmark())["quality_non_regression"] is True

    regressed = paired_benchmark()
    regressed["candidate_scores"]["composition_and_crop"] = 3
    with pytest.raises(ExecutionError, match="Quality gate failed") as quality_error:
        validate_quality_gate(packet, packet, regressed)
    assert any(failure["code"] == "benchmark_regression" for failure in quality_error.value.failures)

    exposure_failed = paired_benchmark()
    exposure_failed["hard_gates"]["visible_adult_exposure_compliance"] = "fail"
    with pytest.raises(ExecutionError, match="Quality gate failed") as hard_gate_error:
        validate_quality_gate(packet, packet, exposure_failed)
    assert any(failure["code"] == "benchmark_hard_gate" for failure in hard_gate_error.value.failures)

    action_failed = paired_benchmark()
    action_failed["hard_gates"]["exposure_action_feasibility"] = "fail"
    with pytest.raises(ExecutionError, match="Quality gate failed") as action_gate_error:
        validate_quality_gate(packet, packet, action_failed)
    assert any(failure["code"] == "benchmark_hard_gate" for failure in action_gate_error.value.failures)
