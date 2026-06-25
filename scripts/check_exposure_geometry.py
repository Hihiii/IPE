#!/usr/bin/env python3
"""Deterministically verify the record-level exposure scene geometry.

This validates the agent's normalized scene plan, not the generated pixels.  It
therefore prevents unsupported claims such as a target being "visible" when
the camera ray, target normal, garment reach, or crop make that impossible.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


EPSILON = 1e-6
FACING_THRESHOLD = 0.25


def _failure(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def _vector(value: Any, field: str, failures: list[dict[str, Any]]) -> tuple[float, float, float] | None:
    if not isinstance(value, list) or len(value) != 3:
        failures.append(_failure("geometry_schema", "Geometry vector must contain exactly three numbers.", field=field))
        return None
    try:
        result = tuple(float(item) for item in value)
    except (TypeError, ValueError):
        failures.append(_failure("geometry_schema", "Geometry vector contains a non-numeric value.", field=field))
        return None
    if not all(math.isfinite(item) for item in result):
        failures.append(_failure("geometry_schema", "Geometry vector contains a non-finite value.", field=field))
        return None
    return result


def _uv(value: Any, field: str, failures: list[dict[str, Any]]) -> tuple[float, float] | None:
    if not isinstance(value, list) or len(value) != 2:
        failures.append(_failure("geometry_schema", "Projected geometry point must contain exactly two numbers.", field=field))
        return None
    try:
        result = tuple(float(item) for item in value)
    except (TypeError, ValueError):
        failures.append(_failure("geometry_schema", "Projected geometry point contains a non-numeric value.", field=field))
        return None
    if not all(math.isfinite(item) and 0.0 <= item <= 1.0 for item in result):
        failures.append(_failure("geometry_range", "Projected geometry point must be normalized to [0, 1].", field=field, actual=result))
        return None
    return result


def _sub(left: tuple[float, float, float], right: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(a - b for a, b in zip(left, right, strict=True))


def _dot(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _length(value: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(value, value))


def _normalize(value: tuple[float, float, float], field: str, failures: list[dict[str, Any]]) -> tuple[float, float, float] | None:
    magnitude = _length(value)
    if magnitude <= EPSILON:
        failures.append(_failure("geometry_zero_vector", "Geometry vector must be non-zero.", field=field))
        return None
    return tuple(component / magnitude for component in value)


def _segment_hits_sphere(
    origin: tuple[float, float, float],
    target: tuple[float, float, float],
    center: tuple[float, float, float],
    radius: float,
) -> bool:
    direction = _sub(target, origin)
    length_squared = _dot(direction, direction)
    if length_squared <= EPSILON:
        return False
    position = max(0.0, min(1.0, _dot(_sub(center, origin), direction) / length_squared))
    closest = tuple(origin[index] + position * direction[index] for index in range(3))
    return _length(_sub(closest, center)) < radius - EPSILON


def _segment_hits_box(
    origin: tuple[float, float, float],
    target: tuple[float, float, float],
    center: tuple[float, float, float],
    half_extents: tuple[float, float, float],
) -> bool:
    direction = _sub(target, origin)
    lower = tuple(center[index] - half_extents[index] for index in range(3))
    upper = tuple(center[index] + half_extents[index] for index in range(3))
    entry, exit = 0.0, 1.0
    for index in range(3):
        if abs(direction[index]) <= EPSILON:
            if origin[index] < lower[index] or origin[index] > upper[index]:
                return False
            continue
        first = (lower[index] - origin[index]) / direction[index]
        second = (upper[index] - origin[index]) / direction[index]
        near, far = min(first, second), max(first, second)
        entry, exit = max(entry, near), min(exit, far)
        if entry > exit:
            return False
    # Intersection at the target itself is acceptable: the target surface is
    # not an occluder.  A blocker must sit strictly before it on the ray.
    return entry < 1.0 - EPSILON and exit > EPSILON


def _occluder_hits_ray(
    value: Any,
    origin: tuple[float, float, float],
    target: tuple[float, float, float],
    failures: list[dict[str, Any]],
    index: int,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        failures.append(_failure("geometry_occluder_schema", "Occluder must be a mapping.", index=index))
        return None
    kind = value.get("kind")
    shape = value.get("shape")
    if kind not in {"limb", "garment", "prop"} or shape not in {"sphere", "box"}:
        failures.append(_failure("geometry_occluder_schema", "Occluder kind or shape is invalid.", index=index, kind=kind, shape=shape))
        return None
    center = _vector(value.get("center"), f"occluders[{index}].center", failures)
    if center is None:
        return None
    hit = False
    if shape == "sphere":
        radius = value.get("radius")
        if not isinstance(radius, (int, float)) or not math.isfinite(float(radius)) or float(radius) <= 0:
            failures.append(_failure("geometry_occluder_schema", "Sphere occluder needs a positive radius.", index=index))
            return None
        hit = _segment_hits_sphere(origin, target, center, float(radius))
    else:
        extents = _vector(value.get("half_extents"), f"occluders[{index}].half_extents", failures)
        if extents is None or any(item <= 0 for item in extents):
            if extents is not None:
                failures.append(_failure("geometry_occluder_schema", "Box occluder needs positive half extents.", index=index))
            return None
        hit = _segment_hits_box(origin, target, center, extents)
    return {"id": value.get("id", f"occluder_{index}"), "kind": kind, "shape": shape} if hit else None


def _review_matches_geometry(review: Any, checks: dict[str, bool], failures: list[dict[str, Any]]) -> None:
    if not isinstance(review, dict):
        failures.append(_failure("geometry_review_missing", "Exposure feasibility review is required for geometry reconciliation."))
        return
    review_fields = {
        "surface_facing": checks["surface_facing"],
        "camera_ray_clear": checks["ray_clear"],
        "action_reach": checks["action_reach"],
        "target_in_crop": checks["crop_inclusion"],
    }
    for field, passed in review_fields.items():
        expected = "pass" if passed else "fail"
        if review.get(field) != expected:
            failures.append(_failure("geometry_review_mismatch", "Phase 4 feasibility receipt does not match deterministic geometry.", field=field, expected=expected, actual=review.get(field)))


def check_exposure_geometry(packet: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """Validate the required normalized camera-to-target exposure geometry."""

    if "exposure_action_plan" not in packet.get("required_claims", []):
        return {"valid": True, "required": False, "checks": {}, "failures": [], "failure_taxonomy": []}

    failures: list[dict[str, Any]] = []
    plan = record.get("exposure_geometry_plan")
    if not isinstance(plan, dict):
        return {
            "valid": False,
            "required": True,
            "checks": {},
            "failures": [_failure("exposure_geometry_plan_missing", "Eligible adult exposure scene is missing exposure_geometry_plan.")],
            "failure_taxonomy": ["missing_geometry_plan"],
        }
    if plan.get("coordinate_system") != "camera_normalized_v1":
        failures.append(_failure("geometry_coordinate_system", "Geometry plan must use camera_normalized_v1.", actual=plan.get("coordinate_system")))

    camera = plan.get("camera")
    target = plan.get("target")
    crop = plan.get("crop_bounds")
    garment_action = plan.get("garment_action")
    if not isinstance(camera, dict) or not isinstance(target, dict) or not isinstance(crop, dict) or not isinstance(garment_action, dict):
        failures.append(_failure("geometry_schema", "Geometry plan needs camera, target, crop_bounds, and garment_action mappings."))
        return {"valid": False, "required": True, "checks": {}, "failures": failures, "failure_taxonomy": [item["code"] for item in failures]}

    camera_position = _vector(camera.get("position"), "camera.position", failures)
    camera_forward = _vector(camera.get("forward"), "camera.forward", failures)
    target_center = _vector(target.get("center"), "target.center", failures)
    surface_normal = _vector(target.get("surface_normal"), "target.surface_normal", failures)
    projected_point = _uv(target.get("projected_point"), "target.projected_point", failures)
    crop_min = _uv(crop.get("min"), "crop_bounds.min", failures)
    crop_max = _uv(crop.get("max"), "crop_bounds.max", failures)
    action_anchor = _vector(garment_action.get("anchor"), "garment_action.anchor", failures)
    reach_radius = garment_action.get("reach_radius")
    if not isinstance(reach_radius, (int, float)) or not math.isfinite(float(reach_radius)) or float(reach_radius) < 0:
        failures.append(_failure("geometry_schema", "garment_action.reach_radius must be a finite non-negative number."))

    if any(value is None for value in (camera_position, camera_forward, target_center, surface_normal, projected_point, crop_min, crop_max, action_anchor)) or failures:
        return {"valid": False, "required": True, "checks": {}, "failures": failures, "failure_taxonomy": sorted({item["code"] for item in failures})}
    assert camera_position and camera_forward and target_center and surface_normal and projected_point and crop_min and crop_max and action_anchor
    if crop_min[0] > crop_max[0] or crop_min[1] > crop_max[1]:
        failures.append(_failure("geometry_crop_bounds", "Crop minimum must not exceed crop maximum.", min=crop_min, max=crop_max))
    forward = _normalize(camera_forward, "camera.forward", failures)
    normal = _normalize(surface_normal, "target.surface_normal", failures)
    camera_to_target = _normalize(_sub(target_center, camera_position), "camera_to_target", failures)
    if forward is None or normal is None or camera_to_target is None or failures:
        return {"valid": False, "required": True, "checks": {}, "failures": failures, "failure_taxonomy": sorted({item["code"] for item in failures})}

    # A front-facing surface has its normal pointing toward the camera.
    target_to_camera = tuple(-component for component in camera_to_target)
    facing_dot = _dot(normal, target_to_camera)
    forward_dot = _dot(forward, camera_to_target)
    surface_facing = facing_dot >= FACING_THRESHOLD and forward_dot > 0.0

    hits: list[dict[str, Any]] = []
    occluders = plan.get("occluders", [])
    if not isinstance(occluders, list):
        failures.append(_failure("geometry_occluder_schema", "occluders must be a list."))
        occluders = []
    for index, occluder in enumerate(occluders):
        hit = _occluder_hits_ray(occluder, camera_position, target_center, failures, index)
        if hit is not None:
            hits.append(hit)
    ray_clear = not hits and not failures
    action_reach = _length(_sub(action_anchor, target_center)) <= float(reach_radius) + EPSILON
    crop_inclusion = crop_min[0] <= projected_point[0] <= crop_max[0] and crop_min[1] <= projected_point[1] <= crop_max[1]
    checks = {
        "surface_facing": surface_facing,
        "ray_clear": ray_clear,
        "action_reach": action_reach,
        "crop_inclusion": crop_inclusion,
        "occluder_free": ray_clear,
    }
    if not surface_facing:
        failures.append(_failure("geometry_surface_backfacing", "Target surface does not face the camera.", facing_dot=round(facing_dot, 6), threshold=FACING_THRESHOLD))
    if hits:
        failures.append(_failure("geometry_ray_occluded", "Camera-to-target ray intersects an occluder.", occluders=hits))
    if not action_reach:
        failures.append(_failure("geometry_action_unreachable", "Garment action anchor cannot physically reach the target.", distance=round(_length(_sub(action_anchor, target_center)), 6), reach_radius=reach_radius))
    if not crop_inclusion:
        failures.append(_failure("geometry_target_out_of_crop", "Target projection lies outside crop bounds.", projected_point=projected_point, crop_min=crop_min, crop_max=crop_max))
    _review_matches_geometry(record.get("exposure_feasibility_review"), checks, failures)
    return {
        "valid": not failures,
        "required": True,
        "checks": checks,
        "trace": {"facing_dot": round(facing_dot, 6), "camera_alignment_dot": round(forward_dot, 6), "occluder_hits": hits},
        "failures": failures,
        "failure_taxonomy": sorted({item["code"] for item in failures}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    record = json.loads(args.record.read_text(encoding="utf-8"))
    result = check_exposure_geometry(packet, record)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
