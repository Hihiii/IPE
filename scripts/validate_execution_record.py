#!/usr/bin/env python3
"""Validate an agent phase ledger and output only a valid ComfyUI prompt pack."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.execution_runtime import ExecutionError, validate_execution_record
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from execution_runtime import ExecutionError, validate_execution_record


def write_failure_trace(packet: dict, error: ExecutionError, requested_path: Path | None) -> Path:
    destination = requested_path or Path(tempfile.gettempdir()) / f"nsfw-execution-failure-{packet.get('packet_id', 'unknown')}.json"
    destination = destination.expanduser().resolve()
    trace = {
        "packet_id": packet.get("packet_id"),
        "catalog_hash": packet.get("catalog_hash"),
        "request_fingerprint": packet.get("packet_hash"),
        "selected_nodes": packet.get("selected_nodes", []),
        "source_hashes": [
            {"path": source["path"], "source_hash": source["source_hash"]}
            for item in packet.get("compiled_context", [])
            for source in item.get("sources", [])
        ] + [
            {"path": source["path"], "source_hash": source["source_hash"], "reference_id": source.get("reference_id")}
            for source in packet.get("deferred_references", [])
        ],
        "failures": error.failures,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--failure-trace", type=Path, help="Optional absolute failure-trace destination.")
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    record = json.loads(args.record.read_text(encoding="utf-8"))
    try:
        result = validate_execution_record(packet, record)
    except ExecutionError as error:
        trace = write_failure_trace(packet, error, args.failure_trace)
        print(json.dumps({"valid": False, "failure_trace": str(trace), "failures": error.failures}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(result["prompt_pack"], ensure_ascii=False))


if __name__ == "__main__":
    main()
