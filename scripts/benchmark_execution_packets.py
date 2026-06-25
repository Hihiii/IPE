#!/usr/bin/env python3
"""Measure fixed-complete compiled-context reduction for request fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

try:
    from scripts.execution_runtime import DEFAULT_CATALOG, compile_execution_packet
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from execution_runtime import DEFAULT_CATALOG, compile_execution_packet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True, help="YAML with a cases list containing id, request, and optional features.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, required=True, help="Explicit JSON benchmark destination.")
    args = parser.parse_args()
    fixtures = yaml.safe_load(args.fixtures.read_text(encoding="utf-8"))
    cases = fixtures.get("cases", [])
    results = []
    for case in cases:
        packet = compile_execution_packet(case["request"], case.get("features", []), args.catalog)
        results.append({"id": case["id"], "metrics": packet["metrics"], "selected_nodes": [node["id"] for node in packet["selected_nodes"]]})
    requested_output = args.output.expanduser()
    if not requested_output.is_absolute():
        raise ValueError("--output must be an absolute path.")
    output = requested_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"schema_version": "1.0.0", "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(results), "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
