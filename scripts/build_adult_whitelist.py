#!/usr/bin/env python3
"""Build the NSFW adult-character whitelist from legacy formal profiles.

Only profiles whose ``identity.maturity_profile.status`` is exactly
``confirmed_adult`` are eligible.  The generated data is intentionally flat so
the skill can load a single small profile instead of an 11-file legacy tree.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "config" / "character-ip"
DEFAULT_OUTPUT = ROOT / "config" / "adult-character-whitelist"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping: {path}")
    return value


def as_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def normalize_alias(value: str) -> str:
    """Normalize only case and whitespace; resolver intentionally never fuzzes."""

    return " ".join(value.casefold().split())


def mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def first_strings(*values: Any, limit: int = 12) -> list[str]:
    result: list[str] = []
    for value in values:
        candidates = as_strings(value) if isinstance(value, list) else [value]
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            normalized = candidate.strip()
            if normalized and normalized not in result:
                result.append(normalized)
            if len(result) == limit:
                return result
    return result


def profile_id(directory: Path) -> str:
    relative = directory.relative_to(SOURCE_ROOT / "games") if "games" in directory.parts else directory.relative_to(SOURCE_ROOT / "mixed-media")
    return "--".join(relative.parts)


def build_profile(directory: Path) -> dict[str, Any] | None:
    identity = mapping(load_yaml(directory / "identity.yaml").get("identity"))
    maturity = mapping(identity.get("maturity_profile"))
    if maturity.get("status") != "confirmed_adult":
        return None

    appearance = mapping(load_yaml(directory / "appearance.yaml").get("appearance"))
    face_hair_body = mapping(load_yaml(directory / "face-hair-body.yaml").get("face_hair_body"))
    face = mapping(face_hair_body.get("face"))
    hair = mapping(face_hair_body.get("hair"))
    body = mapping(face_hair_body.get("body"))
    expression = mapping(load_yaml(directory / "expression-gaze.yaml").get("expression_gaze"))
    canonical_path = directory / "outfits" / "canonical.yaml"
    canonical = mapping(load_yaml(canonical_path).get("canonical_outfit")) if canonical_path.exists() else {}
    guards = mapping(load_yaml(directory / "negative-guards.yaml").get("negative_guards"))

    display_name = identity.get("display_name_en") or identity.get("display_name") or directory.name
    aliases = first_strings([display_name], identity.get("aliases"), limit=20)
    visual_anchors = first_strings(
        appearance.get("first_read_features"),
        face.get("distinguishing_features"),
        [hair.get("color"), hair.get("crown_silhouette"), hair.get("bang_structure")],
        [face.get("eye_color"), face.get("face_shape"), body.get("build")],
        limit=16,
    )
    outfit_anchors = first_strings(
        canonical.get("significant_markers", {}).get("required") if isinstance(canonical.get("significant_markers"), dict) else [],
        [canonical.get("outfit_identity_summary")],
        limit=16,
    )
    drift_guards = first_strings(
        guards.get("identity_drift"),
        guards.get("costume_drift"),
        face_hair_body.get("hair", {}).get("forbidden_hair_drift") if isinstance(face_hair_body.get("hair"), dict) else [],
        face_hair_body.get("body", {}).get("forbidden_body_drift") if isinstance(face_hair_body.get("body"), dict) else [],
        limit=30,
    )

    return {
        "schema_version": "1.0.0",
        "character": {
            "id": profile_id(directory),
            "display_name": display_name,
            "aliases": aliases,
            "source_title": identity.get("source_title", "unknown"),
            "adult_status": "confirmed_adult",
            "adult_source_basis": maturity.get("source_basis", "legacy confirmed_adult marker"),
            "identity_summary": appearance.get("identity_summary", ""),
            "visual_anchors": visual_anchors,
            "outfit_anchors": outfit_anchors,
            "style_anchors": first_strings(
                [expression.get("default_expression"), expression.get("gaze_style", {}).get("default") if isinstance(expression.get("gaze_style"), dict) else None],
                limit=6,
            ),
            "drift_guards": drift_guards,
        },
    }


def build_whitelist(output_dir: Path) -> int:
    source = SOURCE_ROOT.resolve()
    output = output_dir.resolve()
    workspace = ROOT.resolve()
    if not output.is_relative_to(workspace):
        raise ValueError("Output must resolve inside the repository workspace.")

    source_available = source.exists()
    if source_available:
        if not source.is_relative_to(workspace) or output == source or source in output.parents:
            raise ValueError("Output directory cannot overlap the legacy source tree.")
        profiles = []
        for identity_path in sorted(source.rglob("identity.yaml")):
            profile = build_profile(identity_path.parent)
            if profile:
                profiles.append(profile)
    else:
        profile_paths = sorted((output / "profiles").glob("*.yaml"))
        if not profile_paths:
            raise ValueError("Legacy source is absent and no existing flattened whitelist is available.")
        profiles = [load_yaml(path) for path in profile_paths]
        for profile in profiles:
            character = mapping(profile.get("character"))
            if character.get("adult_status") != "confirmed_adult":
                raise ValueError("Flattened whitelist contains a non-confirmed-adult profile.")

    alias_counts = Counter(
        normalize_alias(alias)
        for profile in profiles
        for alias in profile["character"]["aliases"]
    )
    aliases: dict[str, str] = {}
    for profile in profiles:
        character = profile["character"]
        unique_aliases = [
            alias for alias in character["aliases"] if alias_counts[normalize_alias(alias)] == 1
        ]
        if not unique_aliases:
            unique_aliases = [f"{character['display_name']} ({character['source_title']})"]
        character["aliases"] = unique_aliases
        for alias in unique_aliases:
            key = normalize_alias(alias)
            existing = aliases.get(key)
            if existing and existing != character["id"]:
                raise ValueError(f"Duplicate alias {alias!r} for {existing} and {character['id']}")
            aliases[key] = character["id"]

    if source_available and output.exists():
        shutil.rmtree(output)
    profiles_dir = output / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    if source_available:
        for profile in profiles:
            character = profile["character"]
            path = profiles_dir / f"{character['id']}.yaml"
            path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")

    index = {
        "schema_version": "1.0.0",
        "name": "adult-character-whitelist",
        "eligibility": "legacy profile maturity_profile.status == confirmed_adult",
        "character_count": len(profiles),
        "characters": [
            {
                "name": profile["character"]["display_name"],
                "game": profile["character"]["source_title"],
            }
            for profile in profiles
        ],
    }
    (output / "index.yaml").write_text(
        yaml.safe_dump(index, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8"
    )
    sidecar = {
        "schema_version": "1.0.0",
        "name": "adult-character-runtime-alias-resolver",
        "resolver_mode": "exact_normalized_alias_only",
        "aliases": {
            normalize_alias(alias): {
                "id": profile["character"]["id"],
                "name": profile["character"]["display_name"],
                "game": profile["character"]["source_title"],
                "profile": f"profiles/{profile['character']['id']}.yaml",
            }
            for profile in profiles
            for alias in profile["character"]["aliases"]
        },
    }
    (output / "runtime-alias-resolver.json").write_text(
        json.dumps(sidecar, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return len(profiles)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    count = build_whitelist(args.output)
    print(f"Built {count} confirmed-adult profiles in {args.output}")


if __name__ == "__main__":
    main()
