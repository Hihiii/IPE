from pathlib import Path

import pytest

from scripts.export_prompt_pack import export_prompt_pack, validate_prompt_pack


VALID_PACK = {
    "z_image_positive_prompt": "clearly adult fictional character, coherent portrait scene",
    "krea2_positive_prompt": "A clearly adult fictional character in a coherent portrait scene.",
    "suggest_resolution": "1024x1536 (2:3)",
}


def test_exporter_requires_all_and_only_contract_fields() -> None:
    assert validate_prompt_pack(VALID_PACK) == VALID_PACK
    with pytest.raises(ValueError, match="missing fields"):
        validate_prompt_pack({"z_image_positive_prompt": "only one field"})
    with pytest.raises(ValueError, match="unexpected fields"):
        validate_prompt_pack({**VALID_PACK, "debug": "not allowed"})
    with pytest.raises(ValueError, match="forbidden positive-only syntax"):
        validate_prompt_pack({**VALID_PACK, "z_image_positive_prompt": "A portrait. [AVOID] bad anatomy"})
    with pytest.raises(ValueError, match="English prompt text"):
        validate_prompt_pack({**VALID_PACK, "z_image_positive_prompt": "成年角色"})
    with pytest.raises(ValueError, match="WIDTHxHEIGHT"):
        validate_prompt_pack({**VALID_PACK, "suggest_resolution": "portrait"})


def test_exporter_writes_only_to_explicit_absolute_path(tmp_path: Path) -> None:
    output = tmp_path / "prompt-pack.txt"
    exported = export_prompt_pack(VALID_PACK, output)
    assert exported == output.resolve()
    text = output.read_text(encoding="utf-8")
    assert "## Z-Image Base+Turbo Positive Prompt" in text
    assert "## Krea2 Positive Prompt" in text
    with pytest.raises(FileExistsError):
        export_prompt_pack(VALID_PACK, output)


def test_exporter_rejects_relative_paths() -> None:
    with pytest.raises(ValueError, match="absolute path"):
        export_prompt_pack(VALID_PACK, Path("prompt-pack.txt"))
