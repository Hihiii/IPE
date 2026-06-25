#!/usr/bin/env python3
"""Compile one request into a deterministic fixed-complete execution packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.execution_runtime import DEFAULT_CATALOG, compile_execution_packet, request_payload
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from execution_runtime import DEFAULT_CATALOG, compile_execution_packet, request_payload


def read_request(args: argparse.Namespace) -> tuple[str, list[str]]:
    if args.input:
        request, features = request_payload(json.loads(args.input.read_text(encoding="utf-8")))
        return request, [*features, *(args.feature or [])]
    return args.request, args.feature or []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--request", help="Natural-language request to compile.")
    source.add_argument("--input", type=Path, help="JSON object with request and optional features.")
    parser.add_argument("--feature", action="append", help="Additional conservative routing feature; may be repeated.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, required=True, help="Explicit JSON execution-packet destination.")
    args = parser.parse_args()
    request, features = read_request(args)
    packet = compile_execution_packet(request, features, args.catalog)
    requested_output = args.output.expanduser()
    if not requested_output.is_absolute():
        raise ValueError("--output must be an absolute path.")
    output = requested_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"packet_id": packet["packet_id"], "metrics": packet["metrics"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
