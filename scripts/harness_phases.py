"""Deterministic auto phase logic for the harness.

Each function takes checkpoint data from prior phases and returns
the checkpoint data for the current phase.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUTFIT_LIBRARY_DIR = ROOT / "config" / "nsfw-outfit-library"
OUTFIT_INDEX_PATH = OUTFIT_LIBRARY_DIR / "index.yaml"
DEFAULT_CATALOG = ROOT / "config" / "execution-catalog.yaml"

NUDE_TRIGGERS = frozenset(["全裸", "裸體", "不穿", "nude", "naked", "fully nude", "completely nude", "bare"])


# ---------------------------------------------------------------------------
# Phase 0 helpers (used by harness main)
# ---------------------------------------------------------------------------

def compile_packet(request: str, output_path: str | None = None) -> dict[str, Any]:
    """Compile one execution packet without a CLI/temporary-file round trip."""
    try:
        from scripts.execution_runtime import compile_execution_packet
    except ModuleNotFoundError:  # pragma: no cover - direct script execution
        from execution_runtime import compile_execution_packet
    return compile_execution_packet(request)


def materialize_phase(packet: dict[str, Any], phase_id: str) -> dict[str, Any]:
    """Materialize the packet-mandated context for one phase in-process."""
    try:
        from scripts.execution_runtime import materialize_phase_context
    except ModuleNotFoundError:  # pragma: no cover - direct script execution
        from execution_runtime import materialize_phase_context
    return materialize_phase_context(packet, phase_id)


# ---------------------------------------------------------------------------
# Phase 3: Scene Blueprint (auto)
# ---------------------------------------------------------------------------

def phase_3_scene_blueprint(phase1: dict, phase2: dict) -> dict[str, Any]:
    """Build lighting diagram and scene blueprint from Phase 1-2 decisions."""
    intent = phase1.get("intent", phase1)
    cinematic = phase2.get("cinematic_enrichment", phase2)

    scene = {
        "subject": {
            "type": intent.get("subject_type", "subject"),
            "description": intent.get("hero_element", ""),
            "pose_or_arrangement": "as composed",
            "gaze_direction": "camera",
        },
        "environment": {
            "location": "studio environment",
            "subject_to_bg_distance": "moderate",
            "set_dressing": [],
        },
        "camera": {
            "lens": cinematic.get("lens_strategy", {}).get("focal_length_category", "standard"),
            "aperture": cinematic.get("lens_strategy", {}).get("aperture_intent", "medium"),
            "angle": cinematic.get("lens_strategy", {}).get("camera_height", "eye_level"),
            "framing": _infer_shot_size(cinematic),
            "shooting_distance_m": _infer_distance(cinematic),
        },
        "lighting_diagram": _build_lighting_diagram(cinematic),
        "atmosphere": {
            "mood": _infer_mood(cinematic),
            "haze": "none",
            "bokeh_type": "natural",
            "grain": "none",
        },
    }
    return scene


def _infer_shot_size(cinematic: dict) -> str:
    comp = cinematic.get("composition", {})
    br = comp.get("breathing_room", "comfortable")
    return {"tight": "close-up", "comfortable": "medium", "generous": "full-body"}.get(br, "medium")


def _infer_distance(cinematic: dict) -> float:
    wd = cinematic.get("lens_strategy", {}).get("working_distance", "moderate")
    return {"close": 0.8, "moderate": 1.5, "far": 3.0}.get(wd, 1.5)


def _infer_mood(cinematic: dict) -> str:
    cs = cinematic.get("color_script", {})
    cgi = cs.get("color_grading_intent", "neutral")
    return cgi.replace("_", " ")


def _build_lighting_diagram(cinematic: dict) -> dict:
    light = cinematic.get("lighting_intent", {})
    return {
        "key_light": {
            "modifier": light.get("key_modifier", "softbox"),
            "position": "camera-right" if light.get("key_quality") != "hard" else "camera-left",
            "distance": 1.2,
            "color_temp_K": 5600,
        },
        "fill_light": {
            "modifier": "V-flat white bounce",
            "position": "camera-left",
            "distance": 0.8,
        },
        "rim_light": {
            "modifier": "strip_softbox_30x120" if light.get("rim_or_separation") else "none",
            "position": "back-left",
            "distance": 1.0,
        },
    }


# ---------------------------------------------------------------------------
# Phase 3.1: Prompt Package (auto)
# ---------------------------------------------------------------------------

def phase_3_1_prompt_package(phase1: dict, phase2: dict, phase3: dict, packet: dict) -> dict[str, Any]:
    """Compile categorized prompt package."""
    intent = phase1.get("intent", phase1)
    cinematic = phase2.get("cinematic_enrichment", phase2)
    scene = phase3.get("scene_blueprint", phase3)
    orig = packet.get("request", "")

    mature = intent.get("mature_content", {})
    level = mature.get("level", "safe")

    pkg = {
        "original_prompt": orig,
        "type": {
            "category": intent.get("task_profile", "custom"),
            "use_case": intent.get("usage_context", ""),
        },
        "subject": scene.get("subject", {}).get("description", orig),
        "composition": _build_composition_section(cinematic, scene),
        "style_and_lighting": _build_style_section(cinematic, level),
        "background": scene.get("environment", {}).get("location", "studio"),
        "material": "",
        "atmosphere": scene.get("atmosphere", {}).get("mood", "neutral"),
        "constraints": {
            "must_keep": intent.get("constraint_model", {}).get("hard_locks", []),
            "no_extra_elements": [],
        },
        "output_format": {
            "aspect_ratio": intent.get("aspect_ratio", "1:1"),
            "output_medium": intent.get("output_medium", "digital"),
        },
        "publication_layout": intent.get("publication_layout", {"type": "none"}),
        "quality_tags": ["photorealistic", "professional"],
        "avoid": [],
    }

    if level in ("adult_mature", "adult_explicit"):
        pkg["subject"] = f"clearly adult NSFW {pkg['subject']}"
        pkg.setdefault("quality_tags", []).insert(0, "explicit adult content")

    return pkg


def _build_composition_section(cinematic: dict, scene: dict) -> dict:
    comp = cinematic.get("composition", {})
    camera = scene.get("camera", {})
    return {
        "framing": f"{camera.get('framing', 'medium')} shot",
        "layout": comp.get("rule", "balanced"),
        "subject_placement": "centered",
        "depth_planes": f"{comp.get('depth_layers', 3)} layers",
        "negative_space": "balanced",
    }


def _build_style_section(cinematic: dict, level: str) -> dict:
    cs = cinematic.get("color_script", {})
    light = cinematic.get("lighting_intent", {})
    lens = cinematic.get("lens_strategy", {})
    exp = cinematic.get("exposure_strategy", {})
    gt = cinematic.get("generator_translation", {})

    nsfw_prefix = "explicit adult " if level in ("adult_mature", "adult_explicit") else ""

    return {
        "visual_language": f"{nsfw_prefix}cinematic photography",
        "lighting": {
            "key": f"{light.get('key_quality', 'soft')} light from camera-right",
            "fill": "gentle fill",
            "rim": "present" if light.get("rim_or_separation") else "none",
            "quality": f"{light.get('key_quality', 'soft')} with smooth transition",
        },
        "color_script": {
            "palette": cs.get("palette_type", "complementary"),
            "dominant_colors": cs.get("dominant_colors", ["warm", "neutral"]),
            "grading": cs.get("color_grading_intent", "natural"),
        },
        "exposure": f"{exp.get('style', 'middle_key')}, {exp.get('contrast_ratio', 'medium')} contrast",
        "lens": f"{lens.get('focal_length_category', 'standard')} at {lens.get('aperture_intent', 'medium')}",
        "visible_lighting_effect": gt.get("visible_lighting_effect", ""),
        "visible_depth_effect": gt.get("visible_depth_effect", ""),
        "visible_material_effect": gt.get("visible_material_effect", ""),
    }


# ---------------------------------------------------------------------------
# Phase 4.1: Cleanup (auto)
# ---------------------------------------------------------------------------

def phase_4_1_cleanup(prompt_pkg: dict) -> dict[str, Any]:
    """Remove duplicates and contradictions from prompt package."""
    pkg = dict(prompt_pkg)

    tags = pkg.get("quality_tags", [])
    pkg["quality_tags"] = _dedup_ordered(tags)

    avoid = pkg.get("avoid", [])
    pkg["avoid"] = _dedup_ordered(avoid)

    constraints = pkg.get("constraints", {})
    for key in ("must_keep", "no_extra_elements"):
        if key in constraints:
            constraints[key] = _dedup_ordered(constraints.get(key, []))

    return pkg


def _dedup_ordered(items: list) -> list:
    seen = set()
    result = []
    for item in items:
        key = item.strip().lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# Phase 4.2: Renderer Selection (auto)
# ---------------------------------------------------------------------------

def phase_4_2_renderer(prompt_pkg: dict, packet: dict, phase1: dict) -> dict[str, Any]:
    """Render the one supported delivery target: Z-Image."""
    model_target = "z_image"
    profile = "dense_visual_phrase_chain"
    positive = _render_positive(prompt_pkg, model_target, phase1)
    negative = _render_negative(prompt_pkg, model_target, phase1)

    return {
        "model_target": model_target,
        "renderer_profile": profile,
        "positive_prompt": positive,
        "negative_prompt": negative,
        "suggest_resolution": _resolve_resolution(prompt_pkg),
    }


def _render_positive(pkg: dict, target: str, phase1: dict | None = None) -> str:
    parts = []
    subj = pkg.get("subject", "")
    exposure_prefix = _render_exposure_prefix(subj, phase1 or {})
    if exposure_prefix:
        parts.append(exposure_prefix)
        subj = ""
    if subj:
        parts.append(subj)

    comp = pkg.get("composition", {})
    if comp.get("framing"):
        parts.append(comp["framing"])

    style = pkg.get("style_and_lighting", {})
    if isinstance(style, dict):
        for key in ("visible_lighting_effect", "visible_depth_effect", "visible_material_effect"):
            val = style.get(key, "")
            if val:
                parts.append(val)
        light = style.get("lighting", {})
        if isinstance(light, dict) and light.get("key"):
            parts.append(light["key"])

    bg = pkg.get("background", "")
    if bg and bg != "studio":
        parts.append(bg)

    mat = pkg.get("material", "")
    if mat:
        parts.append(mat)

    if target == "z_image":
        tags = pkg.get("quality_tags", [])
        if tags:
            parts.extend(tags)
        return ", ".join(parts)

    return ". ".join(p for p in parts if p)


def _render_negative(pkg: dict, target: str, phase1: dict | None = None) -> str:
    avoid = list(pkg.get("avoid", []))
    contract = (phase1 or {}).get("visible_exposure_contract") or (phase1 or {}).get("exposure_contract") or {}
    evidence_target = contract.get("evidence_target")
    if evidence_target == "nipple":
        avoid.extend(["fully clothed", "intact opaque coverage", "obscured nipple", "cropped nipple"])
    elif evidence_target == "vulva":
        avoid.extend(["fully clothed", "intact opaque coverage", "obscured vulva", "cropped vulva"])
    if contract:
        avoid.extend(["underage", "minor", "childlike", "youthful appearance", "blurred anatomy", "bad anatomy", "cropped body"])
    return ", ".join(_dedup_ordered(avoid)) if avoid else "(not specified)"


def _render_exposure_prefix(subject: str, phase1: dict) -> str:
    contract = phase1.get("visible_exposure_contract") or phase1.get("exposure_contract") or {}
    action = phase1.get("exposure_action_plan") or {}
    if not contract:
        return ""
    evidence_target = contract.get("evidence_target")
    base_subject = _strip_adult_delivery_prefix(subject or phase1.get("hero_element") or "adult subject")
    if evidence_target == "nipple":
        return (
            f"clearly adult nude {base_subject}, nude direct bare presentation, visible nipple unobscured in frame, "
            "nipple in frame on bare skin, relaxed supported adult reclining pose"
        )
    if evidence_target == "vulva":
        return (
            f"clearly adult nude {base_subject}, nude direct bare presentation, visible vulva unobscured in frame, "
            "vulva in frame on bare skin, relaxed supported adult reclining pose"
        )
    if action.get("end_state") == "adult_bare_anatomy_visible":
        return (
            f"clearly adult nude {base_subject}, nude adult body with bare adult anatomy visible, "
            "unobscured in frame, relaxed supported adult reclining pose"
        )
    return f"clearly adult nude {base_subject}, unobscured adult NSFW presentation in frame"


def _strip_adult_delivery_prefix(subject: str) -> str:
    prefixes = (
        "clearly adult nude ",
        "clearly adult nsfw ",
        "clearly adult ",
        "adult nsfw ",
    )
    cleaned = subject.strip()
    lowered = cleaned.lower()
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if lowered.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                lowered = cleaned.lower()
                changed = True
                break
    return cleaned or "adult subject"


def _resolve_resolution(pkg: dict) -> str:
    ar = pkg.get("output_format", {}).get("aspect_ratio", "1:1")
    mapping = {
        "1:1": "1024x1024 (1:1)",
        "4:3": "1216x912 (4:3)",
        "3:4": "912x1216 (3:4)",
        "16:9": "1344x768 (16:9)",
        "9:16": "768x1344 (9:16)",
        "2:3": "1024x1536 (2:3)",
        "3:2": "1536x1024 (3:2)",
    }
    return mapping.get(ar, "1024x1536 (2:3)")


# ---------------------------------------------------------------------------
# Phase 4.3: Delivery Package (auto)
# ---------------------------------------------------------------------------

def phase_4_3_delivery(renderer_out: dict) -> dict[str, Any]:
    """Normalize renderer output to standard delivery contract."""
    return {
        "model_target": "z_image",
        "renderer_profile": renderer_out.get("renderer_profile", "unknown"),
        "publication_mode": "none",
        "positive_prompt": renderer_out.get("positive_prompt", ""),
        "negative_prompt": renderer_out.get("negative_prompt", "(not specified)"),
        "locked_constraints": [],
        "exact_text": [],
        "suggest_resolution": renderer_out.get("suggest_resolution", "1024x1024"),
        "output_contract": {
            "final_prompt_ready": True,
            "renderer_fields_normalized": True,
            "no_raw_internal_package": True,
        },
    }


# ---------------------------------------------------------------------------
# Phase 5: Final Output (auto)
# ---------------------------------------------------------------------------

def phase_5_output(delivery: dict, orig_request: str) -> dict[str, Any]:
    """Return the strict Z-Image delivery contract."""
    return {
        "z_image_positive_prompt": delivery.get("positive_prompt", ""),
        "z_image_negative_prompt": delivery.get("negative_prompt", ""),
        "suggest_resolution": delivery.get("suggest_resolution", "1024x1536 (2:3)"),
    }


# ---------------------------------------------------------------------------
# Nude trigger detection
# ---------------------------------------------------------------------------

def has_nude_trigger(text: str) -> bool:
    lower = text.lower()
    for kw in NUDE_TRIGGERS:
        if kw in lower:
            return True
    return False


def select_outfit_variant(prompt: str) -> dict | None:
    """Select a random NSFW outfit variant from the library.
    Loads the lightweight index first, then only the matched variant file.
    If a variant trigger matches prompt text, prefer that variant.
    Returns None if library cannot be loaded."""
    try:
        with open(OUTFIT_INDEX_PATH, encoding="utf-8") as f:
            index = yaml.safe_load(f)
    except Exception:
        return None

    variants = index.get("outfit_variants", [])
    if not variants:
        return None

    lower_prompt = prompt.lower()

    # First try to match a trigger
    matched_label = None
    for v in variants:
        for trigger in v.get("triggers", []):
            if trigger.lower() in lower_prompt:
                matched_label = v["label"]
                break
        if matched_label:
            break

    if not matched_label:
        # Stable fallback: identical requests must produce identical packets.
        idx = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest(), 16) % len(variants)
        matched_label = variants[idx]["label"]

    # Load only the matched variant file
    try:
        variant_path = OUTFIT_LIBRARY_DIR / f"{matched_label}.yaml"
        with open(variant_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None
