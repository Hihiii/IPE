#!/usr/bin/env python3
"""Explicitly export one validated Flux/Z-Image prompt pack as UTF-8 text."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "flux_final_prompt",
    "z_image_positive_prompt",
    "z_image_negative_prompt",
    "suggest_resolution",
)
FLUX_FORBIDDEN = ("[avoid]", "negative prompt", "--no")
RESOLUTION_PATTERN = re.compile(r"^\d{2,5}x\d{2,5} \(\d{1,2}:\d{1,2}\)$")


def contains_cjk(value: str) -> bool:
    return any("\u3400" <= character <= "\u9fff" for character in value)


def validate_prompt_pack(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("Prompt pack must be a JSON object.")
    keys = set(payload)
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    unexpected = sorted(keys - set(REQUIRED_FIELDS))
    if missing or unexpected:
        detail = []
        if missing:
            detail.append(f"missing fields: {', '.join(missing)}")
        if unexpected:
            detail.append(f"unexpected fields: {', '.join(unexpected)}")
        raise ValueError("Invalid prompt-pack schema (" + "; ".join(detail) + ").")

    result: dict[str, str] = {}
    for field in REQUIRED_FIELDS:
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string.")
        result[field] = value.strip()
    for field in REQUIRED_FIELDS[:3]:
        if contains_cjk(result[field]):
            raise ValueError(f"{field} must be English prompt text.")
    flux_lower = result["flux_final_prompt"].casefold()
    forbidden = [term for term in FLUX_FORBIDDEN if term in flux_lower]
    if forbidden:
        raise ValueError(f"flux_final_prompt contains forbidden Flux syntax: {', '.join(forbidden)}")
    if not RESOLUTION_PATTERN.fullmatch(result["suggest_resolution"]):
        raise ValueError("suggest_resolution must use WIDTHxHEIGHT (RATIO), for example 1024x1536 (2:3).")
    return result


def render_prompt_pack(pack: dict[str, str]) -> str:
    return "\n".join(
        [
            "## Flux Final Prompt",
            pack["flux_final_prompt"],
            "",
            "## Z-Image Final Positive Prompt",
            pack["z_image_positive_prompt"],
            "",
            "## Z-Image Final Negative Prompt",
            pack["z_image_negative_prompt"],
            "",
            "## Suggested Resolution",
            pack["suggest_resolution"],
            "",
        ]
    )


def export_prompt_pack(payload: Any, output: Path) -> Path:
    pack = validate_prompt_pack(payload)
    resolved_output = output.expanduser().resolve()
    if not output.is_absolute():
        raise ValueError("--output must be an absolute path; exports are always explicit.")
    if resolved_output.exists():
        raise FileExistsError(f"Refusing to overwrite existing export: {resolved_output}")
    if resolved_output.suffix.lower() != ".txt":
        raise ValueError("--output must have a .txt extension.")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(render_prompt_pack(pack), encoding="utf-8")
    return resolved_output


def read_payload(input_path: Path | None) -> Any:
    if input_path:
        return json.loads(input_path.read_text(encoding="utf-8"))
    import sys

    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("Provide a JSON input file or JSON on stdin.")
    return json.loads(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="JSON prompt-pack input. Reads stdin when omitted.")
    parser.add_argument("--output", type=Path, required=True, help="Absolute .txt export path.")
    args = parser.parse_args()
    print(export_prompt_pack(read_payload(args.input), args.output))


if __name__ == "__main__":
    main()
