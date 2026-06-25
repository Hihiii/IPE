#!/usr/bin/env python3
"""Materialize every packet-required reference-only source at one phase."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.execution_runtime import materialize_phase_context
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from execution_runtime import materialize_phase_context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--output", type=Path, help="Optional absolute JSON materialization destination.")
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    result = materialize_phase_context(packet, args.phase)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output.expanduser()
        if not output.is_absolute():
            raise ValueError("--output must be an absolute path.")
        output = output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
