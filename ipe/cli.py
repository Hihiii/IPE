from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from .capsule_retriever import build_capsules, validate_capsules
from .phase_engine import debug_phase, inspect_request, run_pipeline
from .subject_intent_parser import BlockedPromptError
from .validator import validate_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ipe", description="Agentic Visual Prompt RAG runtime.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the full prompt-only runtime.")
    run.add_argument("--request", required=True)
    run.add_argument("--json", action="store_true", help="Print JSON instead of text fields.")
    run.add_argument("--debug", action="store_true", help="Include debug metadata in JSON output.")
    run.add_argument("--session", type=Path, help="Optional session directory for artifacts.")

    inspect = sub.add_parser("inspect", help="Inspect intent, module routing, capsules, and phase plan.")
    inspect.add_argument("--request", required=True)
    inspect.add_argument("--json", action="store_true")

    phase = sub.add_parser("phase", help="Materialize full YAML debug context for one phase.")
    phase.add_argument("--session", type=Path, required=True)
    phase.add_argument("--phase", required=True)

    validate = sub.add_parser("validate", help="Validate a runtime session.")
    validate.add_argument("--session", type=Path, required=True)

    benchmark = sub.add_parser("benchmark", help="Run prompt regression cases.")
    benchmark.add_argument("--cases", type=Path, required=True)
    benchmark.add_argument("--json", action="store_true")

    capsules = sub.add_parser("capsules", help="Build or validate compact module capsules.")
    capsules.add_argument("--validate", action="store_true")
    capsules.add_argument("--build", action="store_true")
    capsules.add_argument("--overwrite", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            payload = run_pipeline(args.request, session=args.session, include_debug=args.debug)
            if args.json or args.debug:
                _print_json(payload)
            else:
                _print_prompt_pack(payload)
            return 0
        if args.command == "inspect":
            payload = inspect_request(args.request)
            _print_json(payload) if args.json else _print_json(payload)
            return 0
        if args.command == "phase":
            _print_json(debug_phase(args.session, args.phase))
            return 0
        if args.command == "validate":
            report = validate_session(args.session)
            _print_json(report)
            return 0 if report["valid"] else 1
        if args.command == "benchmark":
            report = run_benchmark(args.cases)
            _print_json(report) if args.json else print(f"{report['passed']}/{report['total']} passed")
            return 0 if report["failed"] == 0 else 1
        if args.command == "capsules":
            if args.build:
                _print_json(build_capsules(overwrite=args.overwrite))
            else:
                _print_json(validate_capsules())
            return 0
    except BlockedPromptError as error:
        _print_json({"blocked": True, "code": error.code, "message": error.message}, stream=sys.stderr)
        return 2
    except Exception as error:
        _print_json({"error": type(error).__name__, "message": str(error)}, stream=sys.stderr)
        return 1
    return 1


def run_benchmark(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    cases = data.get("cases", []) if isinstance(data, dict) else []
    results = []
    for case in cases:
        expected = set(case.get("expected", []))
        try:
            pack = run_pipeline(case["input"])
            blocked = False
            ok = not any(item.startswith("reject") for item in expected)
            detail = "rendered" if ok else "expected rejection but rendered"
        except BlockedPromptError as error:
            pack = None
            blocked = True
            ok = any(item.startswith("reject") for item in expected)
            detail = error.code
        results.append({"id": case.get("id"), "ok": ok, "blocked": blocked, "detail": detail, "prompt_pack": pack})
    failed = [item for item in results if not item["ok"]]
    return {"total": len(results), "passed": len(results) - len(failed), "failed": len(failed), "results": results}


def _print_json(payload: Any, stream: Any = sys.stdout) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=stream)


def _print_prompt_pack(pack: dict[str, str]) -> None:
    print("## Z-Image Final Positive Prompt")
    print(pack["z_image_positive_prompt"])
    print()
    print("## Z-Image Final Negative Prompt")
    print(pack["z_image_negative_prompt"])
    print()
    print("## Suggested Resolution")
    print(pack["suggest_resolution"])


if __name__ == "__main__":
    raise SystemExit(main())
