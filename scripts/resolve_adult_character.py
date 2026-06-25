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


def normalize_alias(value: str) -> str:
    return " ".join(value.casefold().split())


def resolve_adult_character(query: str, sidecar_path: Path = DEFAULT_SIDECAR) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Character query must be a non-empty string.")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if not isinstance(sidecar, dict) or sidecar.get("resolver_mode") != "exact_normalized_alias_only":
        raise ValueError("Invalid runtime alias resolver sidecar.")
    aliases = sidecar.get("aliases")
    if not isinstance(aliases, dict):
        raise ValueError("Runtime alias resolver sidecar has no aliases mapping.")
    result = aliases.get(normalize_alias(query))
    if not isinstance(result, dict):
        raise LookupError("Unknown or ambiguous adult character alias.")
    required = {"id", "name", "game", "profile"}
    if set(result) != required or not all(isinstance(result[field], str) and result[field] for field in required):
        raise ValueError("Runtime alias resolver returned an invalid profile descriptor.")
    profile_path = (sidecar_path.parent / result["profile"]).resolve()
    if not profile_path.is_relative_to(sidecar_path.parent.resolve()) or not profile_path.is_file():
        raise ValueError("Runtime alias resolver profile path escapes the whitelist.")
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    character = profile.get("character") if isinstance(profile, dict) else None
    if not isinstance(character, dict) or character.get("id") != result["id"] or character.get("adult_status") != "confirmed_adult":
        raise ValueError("Runtime alias resolver profile is not a matching confirmed-adult profile.")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--sidecar", type=Path, default=DEFAULT_SIDECAR)
    args = parser.parse_args()
    try:
        result = resolve_adult_character(args.query, args.sidecar)
    except (OSError, ValueError, LookupError, json.JSONDecodeError) as error:
        print(json.dumps({"matched": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"matched": True, "profile": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
