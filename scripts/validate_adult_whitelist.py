#!/usr/bin/env python3
"""Validate the flattened adult-character whitelist and its lookup index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "config" / "adult-character-whitelist"
REQUIRED_CHARACTER_FIELDS = {
    "id",
    "display_name",
    "aliases",
    "source_title",
    "adult_status",
    "adult_source_basis",
    "identity_summary",
    "visual_anchors",
    "outfit_anchors",
    "style_anchors",
    "drift_guards",
}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return value


def normalize_alias(value: str) -> str:
    return " ".join(value.casefold().split())


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON mapping: {path}")
    return value


def validate_whitelist(root: Path) -> list[str]:
    errors: list[str] = []
    index_path = root / "index.yaml"
    if not index_path.exists():
        return [f"Missing whitelist index: {index_path}"]
    index = load_yaml(index_path)
    rows = index.get("characters")
    if not isinstance(rows, list):
        return ["index.yaml characters must be a list"]
    if index.get("character_count") != len(rows):
        errors.append("index.yaml character_count does not match characters length")
    if len(rows) < 100:
        errors.append(f"Unexpectedly few confirmed-adult profiles: {len(rows)}")

    index_pairs: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"name", "game"}:
            errors.append(f"Index rows must contain only name and game: {row!r}")
            continue
        name, game = row.get("name"), row.get("game")
        if not isinstance(name, str) or not name.strip() or not isinstance(game, str) or not game.strip():
            errors.append(f"Invalid minimal index row: {row!r}")
            continue
        index_pairs.append((name, game))

    sidecar_path = root / "runtime-alias-resolver.json"
    if not sidecar_path.exists():
        errors.append(f"Missing runtime alias resolver sidecar: {sidecar_path}")
        sidecar: dict[str, Any] = {}
    else:
        try:
            sidecar = load_json(sidecar_path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"Invalid runtime alias resolver sidecar: {error}")
            sidecar = {}
    aliases = sidecar.get("aliases") if isinstance(sidecar, dict) else None
    if sidecar.get("schema_version") != "1.0.0" or sidecar.get("resolver_mode") != "exact_normalized_alias_only" or not isinstance(aliases, dict):
        errors.append("runtime alias resolver sidecar has an invalid schema")
        aliases = {}

    profiles_by_id: dict[str, tuple[dict[str, Any], Path]] = {}
    seen_aliases: dict[str, str] = {}
    profile_files = sorted((root / "profiles").glob("*.yaml")) if (root / "profiles").exists() else []
    for profile_path in profile_files:
        profile = load_yaml(profile_path)
        character = profile.get("character")
        if not isinstance(character, dict):
            errors.append(f"{profile_path.name}: missing character mapping")
            continue
        missing = REQUIRED_CHARACTER_FIELDS - set(character)
        if missing:
            errors.append(f"{profile_path.name}: missing fields {sorted(missing)}")
        character_id = character.get("id")
        if not isinstance(character_id, str) or not character_id:
            errors.append(f"{profile_path.name}: invalid id")
            continue
        if character_id in profiles_by_id:
            errors.append(f"Duplicate character id: {character_id}")
        profiles_by_id[character_id] = (character, profile_path)
        if character.get("adult_status") != "confirmed_adult":
            errors.append(f"{profile_path.name}: adult_status must be confirmed_adult")
        if not isinstance(character.get("aliases"), list) or not character["aliases"]:
            errors.append(f"{profile_path.name}: aliases must be a non-empty list")
            continue
        for alias in character["aliases"]:
            if not isinstance(alias, str) or not alias.strip():
                errors.append(f"{profile_path.name}: invalid alias")
                continue
            key = normalize_alias(alias)
            previous = seen_aliases.get(key)
            if previous and previous != character_id:
                errors.append(f"Duplicate alias {alias!r}: {previous}, {character_id}")
            seen_aliases[key] = character_id

    if len(profile_files) != len(rows):
        errors.append(f"Profile file count {len(profile_files)} does not match index count {len(rows)}")
    profile_pairs = sorted((str(character.get("display_name")), str(character.get("source_title"))) for character, _ in profiles_by_id.values())
    if sorted(index_pairs) != profile_pairs:
        errors.append("index.yaml name/game rows do not match confirmed-adult profiles")

    if set(aliases) != set(seen_aliases):
        errors.append("runtime alias resolver aliases do not exactly match profile aliases")
    for alias, character_id in seen_aliases.items():
        entry = aliases.get(alias)
        if not isinstance(entry, dict):
            errors.append(f"runtime alias resolver has no mapping for {alias!r}")
            continue
        profile = profiles_by_id.get(character_id)
        expected_profile = f"profiles/{character_id}.yaml"
        if profile is None:
            errors.append(f"runtime alias resolver references unknown id {character_id}")
            continue
        character, _ = profile
        expected = {"id": character_id, "name": character.get("display_name"), "game": character.get("source_title"), "profile": expected_profile}
        if entry != expected:
            errors.append(f"runtime alias resolver mapping mismatch for {alias!r}")
        profile_path = (root / str(entry.get("profile", ""))).resolve()
        if not profile_path.is_relative_to(root.resolve()) or not profile_path.is_file():
            errors.append(f"runtime alias resolver profile path is unsafe for {alias!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    errors = validate_whitelist(args.root)
    if errors:
        print("Adult whitelist validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"OK: adult whitelist at {args.root} is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
