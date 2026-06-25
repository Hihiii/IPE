import json
from pathlib import Path

import pytest

from scripts.resolve_adult_character import resolve_adult_character
from scripts.validate_adult_whitelist import validate_whitelist


ROOT = Path(__file__).resolve().parents[1]


def test_adult_whitelist_is_valid() -> None:
    assert validate_whitelist(ROOT / "config" / "adult-character-whitelist") == []


def test_index_is_minimal_and_runtime_resolver_returns_one_safe_profile() -> None:
    whitelist = ROOT / "config" / "adult-character-whitelist"
    import yaml

    index = yaml.safe_load((whitelist / "index.yaml").read_text(encoding="utf-8"))
    assert all(set(row) == {"name", "game"} for row in index["characters"])
    result = resolve_adult_character("  TIFA   LOCKHART  ")
    assert set(result) == {"id", "name", "game", "profile"}
    assert result["name"] == "Tifa Lockhart"
    assert (whitelist / result["profile"]).is_file()
    sidecar = json.loads((whitelist / "runtime-alias-resolver.json").read_text(encoding="utf-8"))
    assert "aliases" in sidecar
    with pytest.raises(LookupError):
        resolve_adult_character("not-a-whitelisted-adult")
