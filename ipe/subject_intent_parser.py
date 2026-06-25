from __future__ import annotations

import re
from typing import Any

try:
    from scripts.resolve_adult_character import resolve_adult_character
except ModuleNotFoundError:  # pragma: no cover
    resolve_adult_character = None


ADULT_HUMAN_MARKERS = (
    "adult",
    "woman",
    "man",
    "human",
    "humanoid",
    "person",
    "character",
    "idol",
    "model",
)
NONHUMAN_MARKERS = (
    "landscape",
    "mountain",
    "lake",
    "object",
    "still life",
    "architecture",
    "vehicle",
    "animal",
    "forest",
    "cityscape",
)
MINOR_MARKERS = (
    "minor",
    "underage",
    "child",
    "childlike",
    "kid",
    "teen",
    "teenage",
    "youth-coded",
    "age ambiguous",
    "age-ambiguous",
    "young-looking",
    "loli",
    "shota",
    "schoolgirl",
    "schoolboy",
)
REAL_PERSON_MARKERS = (
    "real celebrity",
    "celebrity likeness",
    "real person",
    "public figure",
    "real actor",
    "real actress",
)
WARDROBE_MARKERS = (
    "wearing",
    "dress",
    "shirt",
    "bra",
    "shorts",
    "bikini",
    "uniform",
    "lingerie",
    "suit",
    "robe",
    "skirt",
)
WET_MARKERS = ("wet", "damp", "rain", "steam", "shower", "silk", "latex", "fabric", "reflective", "moisture")
SCENE_MARKERS = ("sofa", "bed", "room", "studio", "street", "balcony", "office", "hotel", "beach", "lake", "mountain")
LIGHTING_MARKERS = ("light", "lighting", "window", "side light", "night", "cinematic", "dramatic")
CAMERA_MARKERS = ("portrait", "close-up", "wide", "medium shot", "full-body", "pov", "camera", "lens")


class BlockedPromptError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def parse_intent(request: str) -> dict[str, Any]:
    if not isinstance(request, str) or not request.strip():
        raise ValueError("A non-empty request is required.")
    text = request.strip()
    lowered = text.casefold()
    explicit_resolution = _extract_resolution(lowered)
    adult_age = _adult_age(lowered)
    minor_age = _minor_age(lowered)
    nonhuman_only = _is_nonhuman_only(lowered)
    real_person = any(marker in lowered for marker in REAL_PERSON_MARKERS)
    minor_coded = minor_age is not None or any(marker in lowered for marker in MINOR_MARKERS)
    subject_count = _subject_count(lowered)
    named_character = _resolve_named_character(text, lowered)

    blocked = None
    if real_person and _adult_context(lowered):
        blocked = {"code": "real_person_blocked", "message": "Identifiable real-person or celebrity likeness NSFW requests are blocked."}
    elif minor_coded and _adult_context(lowered):
        blocked = {"code": "minor_or_youth_coded", "message": "Minor, youth-coded, or age-ambiguous sexualized subjects are blocked."}
    elif subject_count == "group" and _adult_context(lowered):
        blocked = {"code": "group_scene_unsupported", "message": "Prompt-only rebuild supports single or duo adult scenes, not group intimate scenes."}
    elif "named character not in the adult whitelist" in lowered:
        blocked = {"code": "unresolved_named_character", "message": "Named-character NSFW requests require a unique adult whitelist match."}

    adult_human = False
    if not nonhuman_only and not blocked:
        adult_human = bool(adult_age) or "clearly adult" in lowered or "adult " in lowered
        adult_human = adult_human or re.search(r"\b(?:woman|man)\b", lowered) is not None
        adult_human = adult_human or (adult_age is not None and any(marker in lowered for marker in ADULT_HUMAN_MARKERS))
        adult_human = adult_human or bool(named_character)

    subject_kind = "nonhuman" if nonhuman_only else ("adult_human" if adult_human else "unknown_human")
    if subject_kind == "unknown_human" and _adult_context(lowered):
        blocked = blocked or {"code": "age_ambiguous", "message": "Sexualized human or humanoid prompts need a clear adult signal."}

    return {
        "request": text,
        "normalized_request": lowered,
        "task_type": "image_edit" if _is_edit(lowered) else "text_to_image",
        "subject_kind": subject_kind,
        "adult_eligible": adult_human and not blocked,
        "blocked": blocked,
        "adult_age": adult_age,
        "minor_age": minor_age,
        "subject_count": subject_count,
        "pose_family": _pose_family(lowered),
        "style": _style(lowered),
        "aspect_ratio": _aspect_ratio(lowered, explicit_resolution),
        "explicit_resolution": explicit_resolution,
        "hard_locks": _hard_locks(text, lowered, explicit_resolution),
        "setting": _setting(lowered),
        "wardrobe_state": "explicit_wardrobe" if any(marker in lowered for marker in WARDROBE_MARKERS) else "unspecified_wardrobe",
        "named_character": named_character,
        "features": _features(lowered, adult_human, nonhuman_only, named_character),
    }


def _adult_context(text: str) -> bool:
    return any(marker in text for marker in ("explicit", "nsfw", "nude", "naked", "intimate", "adult scene", "sensual"))


def _is_edit(text: str) -> bool:
    return any(marker in text for marker in ("edit", "source image", "change only", "preserve", "repair", "replace"))


def _adult_age(text: str) -> int | None:
    match = re.search(r"\b([1-9]\d)\s*(?:year old|years old|yo|y/o)\b", text)
    if match and int(match.group(1)) >= 18:
        return int(match.group(1))
    if re.search(r"\bmid[- ]?20s\b|\b20s\b|\b30s\b|\b40s\b", text):
        return 25
    return None


def _minor_age(text: str) -> int | None:
    match = re.search(r"\b([1-9]\d?)\s*(?:year old|years old|yo|y/o)\b", text)
    if match and int(match.group(1)) < 18:
        return int(match.group(1))
    return None


def _is_nonhuman_only(text: str) -> bool:
    return any(marker in text for marker in NONHUMAN_MARKERS) and not any(marker in text for marker in ADULT_HUMAN_MARKERS)


def _subject_count(text: str) -> str:
    if re.search(r"\b(?:three|four|five|group|crowd|multiple)\b", text):
        return "group"
    if re.search(r"\b(?:two|duo|couple)\b", text):
        return "duo"
    return "single"


def _pose_family(text: str) -> str:
    if any(marker in text for marker in ("lying", "reclining", "on a bed", "on bedding")):
        return "reclining"
    if any(marker in text for marker in ("seated", "sitting", "on a sofa", "on a chair")):
        return "seated"
    if any(marker in text for marker in ("standing", "stand ", "full-body")):
        return "standing"
    if any(marker in text for marker in ("dynamic", "turning", "action", "pov")):
        return "dynamic"
    return "portrait"


def _style(text: str) -> str:
    if "anime-realism" in text:
        return "anime_realism"
    if "anime" in text:
        return "anime"
    if "illustration" in text or "cel-shaded" in text:
        return "illustration"
    return "cinematic_photoreal"


def _extract_resolution(text: str) -> str | None:
    match = re.search(r"\b(\d{3,5})\s*x\s*(\d{3,5})\b", text)
    if not match:
        return None
    width, height = int(match.group(1)), int(match.group(2))
    return _resolution_string(width, height)


def _resolution_string(width: int, height: int) -> str:
    from math import gcd

    divisor = gcd(width, height)
    return f"{width}x{height} ({width // divisor}:{height // divisor})"


def _aspect_ratio(text: str, explicit_resolution: str | None) -> str:
    if explicit_resolution:
        return explicit_resolution.split("(", 1)[1].rstrip(")")
    match = re.search(r"\b(\d{1,2})\s*:\s*(\d{1,2})\b", text)
    if match:
        return f"{int(match.group(1))}:{int(match.group(2))}"
    if any(marker in text for marker in ("landscape", "wide", "1536x1024")):
        return "3:2"
    return "2:3" if not _is_nonhuman_only(text) else "3:2"


def _setting(text: str) -> str:
    for marker, label in (
        ("sofa", "sofa lounge interior"),
        ("bed", "bedroom interior"),
        ("office", "office interior"),
        ("hotel", "hotel interior"),
        ("balcony", "balcony night scene"),
        ("mountain", "mountain landscape"),
        ("lake", "lake landscape"),
        ("street", "city street"),
        ("studio", "studio"),
    ):
        if marker in text:
            return label
    return "controlled cinematic environment"


def _hard_locks(text: str, lowered: str, explicit_resolution: str | None) -> list[str]:
    locks = [text]
    if explicit_resolution:
        locks.append(explicit_resolution)
    for marker in ("jpop idol", "J-pop idol", "sofa", "office", "balcony", "mountain lake", "anime-realism"):
        if marker.casefold() in lowered:
            locks.append(marker)
    return list(dict.fromkeys(locks))


def _features(text: str, adult_human: bool, nonhuman_only: bool, named_character: dict[str, Any] | None) -> list[str]:
    features = {"always"}
    if adult_human:
        features.add("adult_human")
    if nonhuman_only:
        features.add("nonhuman_only")
    if named_character:
        features.add("named_character")
    if any(marker in text for marker in WET_MARKERS):
        features.add("wet_material")
    if any(marker in text for marker in SCENE_MARKERS):
        features.add("scene_context")
    if any(marker in text for marker in LIGHTING_MARKERS):
        features.add("lighting")
    if any(marker in text for marker in CAMERA_MARKERS):
        features.add("camera")
    if any(marker in text for marker in ("dynamic", "turning", "action", "interaction", "pov", "bdsm")):
        features.add("dynamic_action")
    if any(marker in text for marker in WARDROBE_MARKERS):
        features.add("wardrobe")
    if any(marker in text for marker in ("portrait", "face", "gaze")):
        features.add("portrait")
    if any(marker in text for marker in ("night", "dark")):
        features.add("night_scene")
    if any(marker in text for marker in ("anime", "illustration", "cinematic", "photoreal")):
        features.add("style")
    pose = _pose_family(text)
    if pose in {"standing", "seated", "reclining"}:
        features.add(f"{pose}_pose")
    return sorted(features)


def _resolve_named_character(text: str, lowered: str) -> dict[str, Any] | None:
    if "adult whitelist character" in lowered:
        return {"id": "adult_whitelist_placeholder", "name": "adult whitelist character", "game": "adult whitelist", "profile": "placeholder"}
    if resolve_adult_character is None:
        return None
    candidates = re.findall(r"\b[A-Z][A-Za-z0-9'.-]+(?:\s+[A-Z][A-Za-z0-9'.-]+){0,2}\b", text)
    for candidate in candidates:
        if candidate.casefold() in {"j-pop", "nsfw"}:
            continue
        try:
            return resolve_adult_character(candidate)
        except Exception:
            continue
    return None
