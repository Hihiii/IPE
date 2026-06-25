from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


def load(relative: str) -> dict:
    with (ROOT / relative).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_all_yaml_are_valid_syntax() -> None:
    errors: list[str] = []
    for path in CONFIG.rglob("*.yaml"):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as error:  # pragma: no cover - error output is the assertion value
            errors.append(f"{path.relative_to(ROOT)}: {error}")
    assert not errors, "\n".join(errors)


def test_manifest_routes_cinematic_enhancement_through_nsfw_delivery() -> None:
    manifest = load("config/_manifest.yaml")
    runtime = manifest["execution_runtime"]
    assert runtime["mode"] == "fixed_complete_semantic_closure"
    assert runtime["catalog"] == "config/execution-catalog.yaml"
    assert runtime["quality_contract"] == "config/quality-contract.yaml"
    assert runtime["phase_materializer"] == "scripts/materialize_execution_phase.py"
    assert runtime["geometry_validator"] == "scripts/check_exposure_geometry.py"
    assert runtime["character_resolver"] == "scripts/resolve_adult_character.py"
    assert manifest["always_load"] == [
        "config/core-knowledge.yaml",
        "config/enhancement-pipeline.yaml",
        "config/adult-content-policy.yaml",
        "config/nsfw-baseline-resolver.yaml",
        "config/nsfw-comfyui-overrides.yaml",
        "config/comfyui-prompt-pack.yaml",
        "config/nsfw-dynamic-scene-controller.yaml",
        "config/nsfw-material-environment-controller.yaml",
        "config/nsfw-composition-lighting-controller.yaml",
        "config/nsfw-local-anatomy-surface-controller.yaml",
        "config/nsfw-visual-director.yaml",
    ]
    assert "image_edit" in manifest["conditional_load"]
    assert "named_character" in manifest["conditional_load"]
    assert "adult_human_scene" in manifest["conditional_load"]
    assert manifest["conditional_load"]["visible_adult_exposure"]["path"] == "config/nsfw-visible-exposure-contract.yaml"
    assert manifest["conditional_load"]["exposure_action"]["path"] == "config/nsfw-exposure-action-controller.yaml"
    assert manifest["conditional_load"]["named_character"]["resolver_sidecar"] == "config/adult-character-whitelist/runtime-alias-resolver.json"
    assert "scene_and_visual_enrichment" in manifest["conditional_load"]


def test_cinematic_enhancement_architecture_is_retained() -> None:
    pipeline = load("config/enhancement-pipeline.yaml")
    phase_ids = [phase["id"] for phase in pipeline["pipeline"]]
    assert phase_ids == [
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
    baseline = pipeline["module_routing"]["baseline"]
    assert "config/prompt-core/prompt-assembly-schema.yaml" in baseline
    assert "config/prompt-core/quality-rubric.yaml" in baseline
    assert "config/visual-cinematography/composition-decision-engine.yaml" in baseline
    assert "config/visual-cinematography/camera-technical-router.yaml" in baseline
    assert len(pipeline["composition_decision_order"]) == 14
    assert (CONFIG / "scene-environment" / "physical-collision-guardrails.yaml").exists()
    assert (CONFIG / "character-identity" / "human-anatomy-guardrails.yaml").exists()
    adult_human = pipeline["module_routing"]["adult_human"]
    assert "config/character-identity/adult-standing-pose-system.yaml" in adult_human
    assert "config/character-identity/adult-garment-pose-interaction-system.yaml" in adult_human
    visual = pipeline["module_routing"]["visual_when_relevant"]
    assert "config/visual-cinematography/motion-capture.yaml" in visual
    assert "config/visual-cinematography/style-realism-control.yaml" in visual


def test_dynamic_scene_controllers_define_complete_contracts() -> None:
    dynamic = load("config/nsfw-dynamic-scene-controller.yaml")
    material = load("config/nsfw-material-environment-controller.yaml")
    lighting = load("config/nsfw-composition-lighting-controller.yaml")
    anatomy = load("config/nsfw-local-anatomy-surface-controller.yaml")
    director = load("config/nsfw-visual-director.yaml")
    assert dynamic["eligibility"]["allowed_subject_counts"] == ["single", "duo"]
    assert dynamic["dynamic_scene_plan"]["required_fields"] == [
        "subject_count",
        "pose_family",
        "motion_state",
        "primary_action",
        "support_points",
        "contact_anchors",
        "force_direction",
        "occlusion_order",
        "gaze_reaction",
        "secondary_motion",
        "camera_readability",
    ]
    assert "photoreal_surface_translation" in material
    assert "anime_realism_translation" in material
    assert "surface_geometry_orientation_when_relevant" in material["material_environment_plan"]["required_fields"]
    assert "contact_or_fabric_occlusion_when_relevant" in material["material_environment_plan"]["required_fields"]
    assert anatomy["activation"]["required_when_any"]
    assert "mirror_symmetric_local_anatomy" in anatomy["failure_guards"]
    assert director["scope"]["supported_subject_counts"] == ["single", "duo"]
    assert director["scope"]["excluded"] == ["group_or_multi_person_scene"]
    assert director["scope"]["unsupported_scene_handling"]["group_or_multi_person_scene"] == "reject_before_visual_direction"
    assert director["visual_focus_plan"]["default_primary_focus"] == "sensory_zone_or_readable_interaction_zone"
    assert "exposure_visibility_guard_when_relevant" in director["visual_focus_plan"]["required_fields"]
    assert director["focus_and_light_controls"]["sensory_first_priority"][0] == "primary_sensory_or_interaction_zone"
    assert lighting["visual_priority_plan"]["priority_mode"] == "sensory_first"
    assert "wet_cling_or_translucent_fabric" in anatomy["material_interface_rules"]
    assert "local_detail_ignoring_torso_rotation" in anatomy["failure_guards"]
    assert lighting["lighting_environment_plan"]["photoreal_default"]
    assert lighting["lighting_environment_plan"]["anime_realism"]


def test_adult_policy_blocks_disallowed_subjects() -> None:
    policy = load("config/adult-content-policy.yaml")
    blocked = policy["eligibility"]["blocked_subjects"]
    assert "minors" in blocked
    assert "age-ambiguous subjects" in blocked
    assert "identifiable real people or celebrity likenesses" in blocked
    assert policy["product_mode"] == "always_nsfw"
    assert policy["default_mature_tier"] == "adult_nude"
    assert policy["adult_content_tiers"] == ["adult_nude", "explicit_adult"]
    assert policy["eligibility"]["nonhuman_exception"]
    assert policy["scene_limits"]["supported_subject_counts"] == ["single", "duo"]


def test_always_nsfw_baseline_resolver_routes_only_eligible_humans() -> None:
    baseline = load("config/nsfw-baseline-resolver.yaml")
    assert baseline["product_mode"]["id"] == "always_nsfw"
    assert baseline["product_mode"]["default_human_tier"] == "adult_nude"
    assert baseline["subject_resolution"]["human_or_humanoid"]["action"] == "apply_adult_nude_baseline"
    assert baseline["subject_resolution"]["nonhuman_or_object_or_landscape"]["action"] == "preserve_non_nsfw_input"
    wardrobe = baseline["wardrobe_transformation"]
    assert wardrobe["unspecified_wardrobe"]["result"] == "adult_nude_baseline"
    assert "garment_type" in wardrobe["explicit_wardrobe"]["preserve"]
    assert baseline["image_edit_transformation"]["eligible_human_source"]["order"][1] == "apply_adult_nude_baseline_or_wardrobe_transformation"
    assert baseline["visible_exposure_contract"]["source"] == "config/nsfw-visible-exposure-contract.yaml"


def test_visible_exposure_contract_requires_readable_feminine_evidence() -> None:
    exposure = load("config/nsfw-visible-exposure-contract.yaml")
    contract = exposure["visible_exposure_contract"]
    assert contract["required_fields"] == [
        "subject_presentation",
        "wardrobe_state",
        "exposure_requirement",
        "evidence_mode",
        "evidence_target",
        "garment_transformation_action",
        "camera_visibility_guard",
        "forbidden_substitutions",
    ]
    assert exposure["resolution"]["unspecified_wardrobe"]["exposure_requirement"] == "full_nudity_required"
    assert exposure["resolution"]["explicit_wardrobe"]["exposure_requirement"] == "partial_nudity_required"
    assert exposure["resolution"]["female_feminine_evidence"]["allowed_targets"] == ["nipple", "vulva"]
    assert "opaque_full_coverage" in contract["required_forbidden_substitutions"]
    assert "vague_transparency_without_readable_target" in exposure["validation"]["hard_failure_conditions"]


def test_exposure_action_controller_binds_target_to_physical_end_state() -> None:
    action = load("config/nsfw-exposure-action-controller.yaml")
    plan = action["exposure_action_plan"]
    assert plan["required_fields"] == [
        "primary_target",
        "route",
        "garment_zone",
        "action",
        "action_anchor",
        "end_state",
        "material_cause_when_relevant",
        "camera_proof",
        "fallback_route",
    ]
    matrix = action["compatibility_matrix"]
    assert matrix["direct_garment_action"]["nipple"]["garment_zone"] == "upper_body"
    assert matrix["direct_garment_action"]["vulva"]["garment_zone"] == "lower_body"
    assert matrix["direct_garment_action"]["nipple"]["actions"]["pull_open_front_panels_below_target"]["end_state"] == "nipple_fully_uncovered"
    assert action["feasibility_review"]["maximum_recomposition_attempts"] == 3
    assert action["exposure_geometry_plan"]["coordinate_system"] == "camera_normalized_v1"
    assert action["exposure_geometry_plan"]["validation"]["required_checks"] == ["surface_facing", "camera_ray_clear", "action_reach", "crop_inclusion", "occluder_free"]
    assert "Trace the camera-subject-target relationship" in action["phase_hooks"]["phase_4_self_review"]


def test_core_pre_filter_and_reference_only_contracts_are_declared() -> None:
    core = load("config/core-knowledge.yaml")
    catalog = load("config/execution-catalog.yaml")
    quality = load("config/quality-contract.yaml")
    assert core["decision_pre_filter"]["schema_version"] == "1.0.0"
    assert "exposure_route" in core["decision_pre_filter"]["required_decisions"]
    deferred = [source for node in catalog["rule_nodes"] for source in node["sources"] if source.get("load_mode") == "reference_only"]
    assert deferred
    assert all(source["materialize_at_phase"] in catalog["phase_ids"] and source["activate_when"] for source in deferred)
    assert quality["performance"]["minimum_initial_context_reduction_percent"] == 25


def test_comfyui_output_contract_is_complete() -> None:
    renderer = load("config/comfyui-prompt-pack.yaml")
    fields = renderer["output_contract"]["fields"]
    assert fields == [
        "flux_final_prompt",
        "z_image_positive_prompt",
        "z_image_negative_prompt",
        "suggest_resolution",
    ]
    assert renderer["flux"]["forbidden"] == [
        "negative prompt syntax",
        "avoid lists",
        "section headers",
        "workflow instructions",
        "model-specific command flags",
    ]
    assert renderer["resolution_policy"]["buckets"] == {
        "square": "1024x1024 (1:1)",
        "portrait": "1024x1536 (2:3)",
        "landscape": "1536x1024 (3:2)",
    }
    assert renderer["style_translation"]["default"] == "cinematic_photoreal"
    assert len(renderer["internal_scene_contract"]["required_when_human_subject_present"]) == 18
    assert "eligible_human_subject" in renderer["always_nsfw_baseline_rendering"]
    assert "nonhuman_only_subject" in renderer["always_nsfw_baseline_rendering"]
    assert "visual_focus_plan" in renderer["adult_visual_direction_rendering"]
    assert "local_anatomy_surface_when_active" in renderer["adult_visual_direction_rendering"]
    assert renderer["flux"]["required_order"][1] == "visible_adult_exposure_evidence"
    assert renderer["z_image"]["positive_required_order"][1] == "visible_adult_exposure_evidence"
    assert "exposure_geometry_plan" in renderer["always_nsfw_baseline_rendering"]
    assert any("decal-like" in rule for rule in renderer["z_image"]["negative_policy"])
    overrides = load("config/nsfw-comfyui-overrides.yaml")
    assert "chatgpt_image" in overrides["disabled_delivery_targets"]
    assert "stable_diffusion" in overrides["disabled_delivery_targets"]
    assert any("config/comfyui-prompt-pack.yaml" in rule for rule in overrides["override_rules"])
    assert any("adultize the source before applying the requested edit" in rule for rule in overrides["override_rules"])


def test_regression_cases_match_output_contract() -> None:
    cases = load("tests/prompt-regression-cases.yaml")
    renderer = load("config/comfyui-prompt-pack.yaml")
    dynamic = load("config/nsfw-dynamic-scene-controller.yaml")
    assert cases["required_output_fields"] == renderer["output_contract"]["fields"]
    ids = [case["id"] for case in cases["cases"]]
    assert len(ids) == len(set(ids))
    assert {"age_unverified_character", "youth_coded_subject", "real_person_likeness"}.issubset(ids)
    assert {"standing_photoreal", "seated_soft_surface", "reclining_material_response", "duo_peak_action", "anime_realism_dynamic"}.issubset(ids)
    assert {"plain_human_always_nsfw", "clothed_human_transformation", "unspecified_wardrobe_nude_baseline", "human_edit_auto_adultization", "nonhuman_no_nsfw_injection"}.issubset(ids)
    assert {"wet_silk_local_surface", "wet_button_shirt_local_surface", "nude_outdoor_surface_continuity", "single_sensory_focus_wide", "duo_sensory_focus_medium", "pov_camera_relationship", "consensual_bdsm_anchor_readability", "group_scene_rejected", "afterglow_focus_hierarchy", "local_surface_image_edit", "anime_realism_local_surface", "sports_bra_shorts_visible_exposure", "wet_tshirt_visible_evidence", "office_formal_exposure_action"}.issubset(ids)
    dynamic_fields = cases["dynamic_scene_required_fields"]
    assert dynamic_fields == dynamic["dynamic_scene_plan"]["required_fields"]
    for case in cases["cases"]:
        if case.get("requires_dynamic_scene_plan"):
            assert case["must_plan"] == dynamic_fields
