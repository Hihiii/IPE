#!/usr/bin/env python3
"""Reject a migration candidate that lowers coverage, benchmark quality, or efficiency."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from scripts.execution_runtime import DEFAULT_QUALITY_CONTRACT, ExecutionError, validate_quality_gate
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from execution_runtime import DEFAULT_QUALITY_CONTRACT, ExecutionError, validate_quality_gate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-packet", type=Path, required=True)
    parser.add_argument("--candidate-packet", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True, help="Paired manual benchmark JSON.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_QUALITY_CONTRACT)
    args = parser.parse_args()
    try:
        result = validate_quality_gate(
            json.loads(args.legacy_packet.read_text(encoding="utf-8")),
            json.loads(args.candidate_packet.read_text(encoding="utf-8")),
            json.loads(args.benchmark.read_text(encoding="utf-8")),
            args.contract,
        )
    except ExecutionError as error:
        print(json.dumps({"valid": False, "failures": error.failures}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
