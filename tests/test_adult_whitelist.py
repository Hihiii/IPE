import json
from pathlib import Path

import pytest

from scripts.resolve_adult_character import resolve_adult_character
from scripts.validate_adult_whitelist import validate_whitelist


ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "config" / "adult-character-whitelist" / "runtime-alias-resolver.json"


def test_adult_whitelist_is_valid() -> None:
    assert validate_whitelist(ROOT / "config" / "adult-character-whitelist") == []


def test_exact_match_still_works() -> None:
    whitelist = ROOT / "config" / "adult-character-whitelist"
    result = resolve_adult_character("  TIFA   LOCKHART  ")
    assert set(result) == {"id", "name", "game", "profile"}
    assert result["name"] == "Tifa Lockhart"
    assert (whitelist / result["profile"]).is_file()


def test_prefix_match_first_name_only() -> None:
    result = resolve_adult_character("aerith")
    assert result["name"] == "Aerith Gainsborough"
    assert result["game"] == "Final Fantasy VII"


def test_prefix_match_still_respects_exact_alias() -> None:
    result = resolve_adult_character("celes")
    assert result["name"] == "Celes Chere"


def test_prefix_match_with_hint_does_not_interfere() -> None:
    result = resolve_adult_character("cid", hint="Final Fantasy VII")
    assert result["name"] == "Cid Highwind"


def test_unknown_query_raises_error() -> None:
    with pytest.raises(LookupError):
        resolve_adult_character("not-a-whitelisted-adult")


def test_sidecar_has_updated_resolver_mode() -> None:
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
    assert sidecar["resolver_mode"] == "exact_and_prefix_with_hint"
