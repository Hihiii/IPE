#!/usr/bin/env python3
"""Resolve one confirmed-adult character by exact normalized alias.

The sidecar is runtime-only.  It never becomes part of an agent-visible
execution packet; a caller receives only the uniquely matched profile locator.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIDECAR = ROOT / "config" / "adult-character-whitelist" / "runtime-alias-resolver.json"


SUPPORTED_RESOLVER_MODES = ("exact_normalized_alias_only", "exact_and_prefix_with_hint")


def normalize_alias(value: str) -> str:
    return " ".join(value.casefold().split())


def _validate_and_resolve(profile_descriptor: dict[str, Any], sidecar_path: Path) -> dict[str, Any]:
    required = {"id", "name", "game", "profile"}
    if set(profile_descriptor) != required or not all(
        isinstance(profile_descriptor[field], str) and profile_descriptor[field] for field in required
    ):
        raise ValueError("Runtime alias resolver returned an invalid profile descriptor.")
    profile_path = (sidecar_path.parent / profile_descriptor["profile"]).resolve()
    if not profile_path.is_relative_to(sidecar_path.parent.resolve()) or not profile_path.is_file():
        raise ValueError("Runtime alias resolver profile path escapes the whitelist.")
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    character = profile.get("character") if isinstance(profile, dict) else None
    if not isinstance(character, dict) or character.get("id") != profile_descriptor["id"] or character.get("adult_status") != "confirmed_adult":
        raise ValueError("Runtime alias resolver profile is not a matching confirmed-adult profile.")
    return profile_descriptor


def resolve_adult_character(
    query: str,
    sidecar_path: Path = DEFAULT_SIDECAR,
    hint: str = "",
) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Character query must be a non-empty string.")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if not isinstance(sidecar, dict) or sidecar.get("resolver_mode") not in SUPPORTED_RESOLVER_MODES:
        raise ValueError("Invalid runtime alias resolver sidecar.")
    aliases = sidecar.get("aliases")
    if not isinstance(aliases, dict):
        raise ValueError("Runtime alias resolver sidecar has no aliases mapping.")

    norm_query = normalize_alias(query)

    # Phase 1: exact normalized match
    result = aliases.get(norm_query)
    if isinstance(result, dict):
        return _validate_and_resolve(result, sidecar_path)

    # Phase 2: prefix match — query is a word-level prefix of an alias key
    candidates: list[tuple[str, dict[str, Any]]] = []
    for alias_key, profile in aliases.items():
        if not isinstance(profile, dict) or not alias_key.startswith(norm_query):
            continue
        rest = alias_key[len(norm_query):]
        if rest and not rest.startswith(" "):
            continue
        candidates.append((alias_key, profile))

    if len(candidates) == 1:
        return _validate_and_resolve(candidates[0][1], sidecar_path)

    if len(candidates) > 1:
        if hint:
            norm_hint = hint.casefold()
            filtered = [(key, prof) for key, prof in candidates if prof.get("game", "").casefold() in norm_hint]
            if len(filtered) == 1:
                return _validate_and_resolve(filtered[0][1], sidecar_path)
            if filtered:
                candidates = filtered

        names = sorted(f"{prof['name']} ({prof['game']})" for _, prof in candidates)
        raise LookupError(
            f"Ambiguous adult character alias '{query}' matched {len(candidates)} characters: "
            f"{'; '.join(names)}. "
            f"Provide more of the name or add a game/series hint (e.g. --hint 'Final Fantasy VII')."
        )

    raise LookupError("Unknown or ambiguous adult character alias.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--sidecar", type=Path, default=DEFAULT_SIDECAR)
    parser.add_argument("--hint", default="", help="Optional context (e.g. the user request) for disambiguation.")
    args = parser.parse_args()
    try:
        result = resolve_adult_character(args.query, args.sidecar, args.hint)
    except (OSError, ValueError, LookupError, json.JSONDecodeError) as error:
        print(json.dumps({"matched": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"matched": True, "profile": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
