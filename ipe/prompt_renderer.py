from __future__ import annotations

import re
from typing import Any


RESOLUTION_BUCKETS = {
    "1:1": "1024x1024 (1:1)",
    "2:3": "1024x1536 (2:3)",
    "3:2": "1536x1024 (3:2)",
    "3:4": "912x1216 (3:4)",
    "4:3": "1216x912 (4:3)",
    "9:16": "768x1344 (9:16)",
    "16:9": "1344x768 (16:9)",
}


def render_prompt_pack(prompt_package: dict[str, Any]) -> dict[str, str]:
    intent = prompt_package["intent"]
    if intent["subject_kind"] == "nonhuman":
        positive = _nonhuman_positive(prompt_package)
        negative = "people, human subject, nude, NSFW, explicit adult content, distorted perspective, unreadable scene"
    else:
        positive = _adult_positive(prompt_package)
        negative = (
            "underage, minor, childlike, youthful appearance, age-ambiguous subject, real person likeness, "
            "fully clothed, opaque full coverage, obscured adult presentation, cropped subject, blurred anatomy, bad anatomy"
        )
    return {
        "z_image_positive_prompt": _dedup_phrase_chain(positive),
        "z_image_negative_prompt": _dedup_phrase_chain(negative),
        "suggest_resolution": intent.get("explicit_resolution") or RESOLUTION_BUCKETS.get(intent.get("aspect_ratio"), "1024x1536 (2:3)"),
    }


def _adult_positive(prompt_package: dict[str, Any]) -> str:
    intent = prompt_package["intent"]
    blueprint = prompt_package["scene_blueprint"]
    subject = _adult_subject(intent)
    camera = blueprint["camera"]
    lighting = blueprint["lighting"]
    material = blueprint["material"]
    scene = blueprint["scene"]
    style = "anime-realism finish" if intent["style"] == "anime_realism" else "cinematic photoreal finish"
    return (
        f"clearly adult NSFW {subject}, adult nude baseline, readable adult presentation, "
        f"{intent['pose_family']} pose, {camera['framing']}, {camera['lens']}, crop-safe composition, "
        f"{lighting['setup']}, {lighting['exposure']}, {material['surface_detail']}, "
        f"{scene['setting']}, {scene['depth']}, {style}, professional Z-Image prompt detail"
    )


def _nonhuman_positive(prompt_package: dict[str, Any]) -> str:
    intent = prompt_package["intent"]
    blueprint = prompt_package["scene_blueprint"]
    camera = blueprint["camera"]
    lighting = blueprint["lighting"]
    scene = blueprint["scene"]
    return (
        f"{intent['request']}, cinematic environmental composition, {camera['framing']}, {camera['lens']}, "
        f"{lighting['setup']}, {lighting['exposure']}, {scene['setting']}, {scene['depth']}, "
        "natural material detail, professional Z-Image prompt detail"
    )


def _adult_subject(intent: dict[str, Any]) -> str:
    text = intent["request"]
    lowered = intent["normalized_request"]
    if "jpop idol" in lowered or "j-pop idol" in lowered:
        return "25 year old adult J-pop idol lying on sofa" if "25 year old" in lowered else "adult J-pop idol"
    if intent.get("named_character"):
        return f"confirmed adult {intent['named_character']['name']}"
    if re.search(r"\bwoman\b", lowered):
        return "adult fictional woman"
    if re.search(r"\bman\b", lowered):
        return "adult fictional man"
    return "adult fictional human subject"


def _dedup_phrase_chain(value: str) -> str:
    seen = set()
    result = []
    for item in (part.strip() for part in value.split(",")):
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return ", ".join(result)
