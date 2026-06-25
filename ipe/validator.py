from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.export_prompt_pack import validate_prompt_pack

from .constants import PHASES
from .io import load_json, write_json


class ValidationError(ValueError):
    def __init__(self, failures: list[dict[str, Any]]) -> None:
        super().__init__("Runtime validation failed.")
        self.failures = failures


def validate_run(artifacts: dict[str, Any]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    intent = artifacts.get("intent_profile", {})
    module_plan = artifacts.get("module_plan", {})
    ledger = artifacts.get("phase_ledger", {})
    prompt_pack = artifacts.get("prompt_pack")
    access_log = artifacts.get("capsule_access_log", [])

    phase_ids = [entry.get("phase_id") for entry in ledger.get("phases", [])]
    if phase_ids != PHASES:
        failures.append(_failure("phase_order", "$.phase_ledger.phases", "Phase ledger must contain all phases in strict runtime order."))
    for entry in ledger.get("phases", []):
        if entry.get("status") != "complete":
            failures.append(_failure("phase_incomplete", "$.phase_ledger.phases", "Every phase must complete before final output."))

    module_ids = set(module_plan.get("module_ids", []))
    loaded_capsules = {entry.get("module_id") for entry in access_log if entry.get("kind") == "capsule"}
    missing_capsules = sorted(module_ids - loaded_capsules)
    if missing_capsules:
        failures.append(_failure("capsule_coverage", "$.capsule_access_log", "Every selected module must load its capsule.", missing_modules=missing_capsules))

    try:
        validated_pack = validate_prompt_pack(prompt_pack)
    except ValueError as error:
        failures.append(_failure("prompt_pack_schema", "$.prompt_pack", str(error)))
        validated_pack = None

    if validated_pack and intent.get("subject_kind") == "adult_human":
        positive = validated_pack["z_image_positive_prompt"].casefold()
        negative = validated_pack["z_image_negative_prompt"].casefold()
        if not intent.get("adult_eligible"):
            failures.append(_failure("adult_eligibility", "$.intent_profile.adult_eligible", "Adult human output requires adult eligibility."))
        for marker in ("clearly adult", "nsfw", "adult nude baseline"):
            if marker not in positive:
                failures.append(_failure("adult_baseline_prompt", "$.prompt_pack.z_image_positive_prompt", f"Positive prompt missing {marker!r}."))
        for marker in ("underage", "minor", "age-ambiguous"):
            if marker not in negative:
                failures.append(_failure("adult_negative_guard", "$.prompt_pack.z_image_negative_prompt", f"Negative prompt missing {marker!r}."))
    elif validated_pack and intent.get("subject_kind") == "nonhuman":
        positive = validated_pack["z_image_positive_prompt"].casefold()
        if any(marker in positive for marker in ("nsfw", "nude", "clearly adult")):
            failures.append(_failure("nonhuman_nsfw_injection", "$.prompt_pack.z_image_positive_prompt", "Nonhuman-only output must not inject NSFW language."))

    claims = {claim for module in module_plan.get("modules", []) for claim in module.get("claims", [])}
    ledger_claims = {claim for phase in ledger.get("phases", []) for claim in phase.get("claims", [])}
    missing_claims = sorted(claims - ledger_claims)
    if missing_claims:
        failures.append(_failure("claim_coverage", "$.phase_ledger", "Phase ledger must retain selected module claims.", missing_claims=missing_claims))

    report = {"valid": not failures, "failures": failures}
    if failures:
        raise ValidationError(failures)
    return report


def validate_session(session: Path) -> dict[str, Any]:
    artifacts = {
        "intent_profile": load_json(session / "intent_profile.json"),
        "module_plan": load_json(session / "module_plan.json"),
        "phase_ledger": load_json(session / "phase_ledger.json"),
        "capsule_access_log": load_json(session / "capsule_access_log.json"),
        "prompt_pack": load_json(session / "prompt_pack.json"),
    }
    try:
        report = validate_run(artifacts)
    except ValidationError as error:
        report = {"valid": False, "failures": error.failures}
    write_json(session / "validation_report.json", report)
    return report


def _failure(code: str, path: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "path": path, "message": message, **extra}
