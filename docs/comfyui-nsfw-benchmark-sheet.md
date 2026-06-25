# NSFW Cinematic ComfyUI Benchmark Sheet

Use this sheet to evaluate generated images manually without coupling the skill
to a particular ComfyUI workflow. Record one sheet per prompt-pack and model
run; use the same workflow, model revision, seed, sampler, and resolution when
comparing a prompt revision against a baseline.

## Run Metadata

| Field | Value |
| --- | --- |
| Date / reviewer | |
| Workflow identifier | |
| Model and revision | |
| LoRA / control inputs | |
| Seed | |
| Resolution | |
| Style mode | `cinematic_photoreal` / `anime_realism` |
| Regression case ID | |
| Prompt-pack revision | |

## Scorecard

Score each category from 1 to 5. A delivery candidate requires every category
to score at least 3; a score of 1 or 2 creates a targeted prompt revision.

| Category | What to inspect | Score |
| --- | --- | --- |
| Composition and crop | Hierarchy, framing, readable face/action/support zone, silhouette separation | |
| Pose and contact | Center of gravity, support points, hand intent, contact, occlusion, no floating anatomy | |
| Motion and impact | One readable action moment, force direction, timing, controlled secondary motion and blur | |
| Material and tactile response | Cause-driven skin, fabric, bedding, water, glass, and environment response | |
| Local anatomy and surface continuity | Visible local forms follow torso curvature, individual variation, pose, fabric interface, moisture, and key light; no decal-like or mirror-symmetric detail | |
| Visible adult exposure compliance | When the contract applies: the required full/partial nude state is present; selected evidence target is directly visible or clearly discernible through valid sheer material; it is in frame, unobscured, and not replaced by vague wetness, contour, or intact coverage | |
| Action-to-exposure feasibility | The selected target, garment zone, action anchor, end state, material cause, and camera proof form one plausible chain; no cleavage-only, loose-button-only, mismatched garment zone, or unsupported wet-fabric shortcut | |
| Exposure geometry feasibility | Recorded camera ray reaches a camera-facing target surface without limb/garment/prop intersection; garment anchor reaches target and target projection remains inside crop | |
| Focus hierarchy and camera grammar | Declared primary sensory/interaction focus wins; secondary emotional cue, shot scale, angle, depth, occlusion, and crop remain intentional | |
| Lighting and environment | Motivated light, exposure, shadows, reflections/bounce, subject readability | |
| Style consistency | Photoreal or anime-realism rules remain internally consistent | |
| Identity and adult eligibility | Whitelist/original identity preserved; every subject clearly adult | |

## Revision Record

- Failed category:
- Visible failure:
- Keep locked:
- Prompt change:
- Expected visible result:
- Re-run metadata:

Do not change unrelated variables during a targeted revision. If composition,
support, contact, and lighting all fail together, rebuild the scene blueprint
instead of accumulating corrective negative terms.

## Non-Regression Comparison

For a catalog or leaf-rule migration, compare a legacy and candidate prompt pack
with identical workflow, model revision, LoRA/control inputs, seed, resolution,
and style mode. Existing score categories must not be lower in the candidate;
the local-anatomy, focus/camera, visible-exposure, and action-to-exposure
categories must all be at least 3.
Record the scores in the JSON shape consumed by
`scripts/validate_quality_gate.py` and do not promote a migration that fails the
quality gate, even if it reduces context size.

For every adult-human packet, set the benchmark hard-gate value
`visible_adult_exposure_compliance` to `pass` only if the visible-exposure row
passes. A `fail` value blocks promotion regardless of every other score.

For every adult-human packet, also set `exposure_action_feasibility` to `pass`
only if the action-to-exposure row passes. A failed value blocks promotion even
when the target itself appears in the prompt text.

Set `exposure_geometry_feasibility` to `pass` only if the exposure-geometry row
passes. A geometry failure blocks promotion even when textual target claims are
present.
