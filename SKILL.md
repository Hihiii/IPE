---
name: nsfw-comfyui-zimage-cinematic-prompt-enhancer
description: "Always-NSFW cinematic prompt enhancement for eligible adult fictional/original human subjects, rendered for ComfyUI Z-Image."
version: 3.6.0
license: MIT
category: creative
platforms: [linux, windows]
---

# NSFW ComfyUI Cinematic Prompt Enhancer

This skill keeps the original prompt enhancer's cinematic reasoning—composition,
camera, crop, depth, lighting, exposure, materials, anatomy, contact physics,
scene construction, prompt packaging, and self-review—while specializing subject
eligibility and final output for adult NSFW Z-Image use.

## Scope

- Supports text-to-image and reference/image edits.
- Applies an adult-nude cinematic baseline to every eligible human or humanoid
  subject, including prompts with no NSFW wording.
- Preserves an explicit-adult request when it raises the requested content tier.
- Leaves nonhuman-only, object-only, and landscape-only prompts non-NSFW.
- Outputs only a Z-Image Final Positive Prompt, Z-Image Final Negative Prompt,
  and Suggested Resolution.
- Does not output workflow JSON, API calls, sampler settings, or final prompts
  for other image/video models.
- Does not process minors, age-ambiguous or youth-coded sexualized subjects, or
  identifiable real-person likenesses.

## Harness Execution (single entry point)

Do not independently choose config files, scripts, or skip pipeline phases.
The only supported execution route is the harness:

```bash
python3 scripts/harness.py --request "your prompt" --outdir /tmp/harness-work/
```

The harness compiles the packet, then runs each phase in strict order. Every
phase follows the same mechanism:

1. Harness writes `prompt_{phase}.json` with materialized context + JSON schema
2. Harness writes or waits for `response_{phase}.json`
3. Harness validates the response against the schema
4. Harness writes `checkpoint_{phase}.json` and moves to the next phase

| # | Phase | Description |
|---|-------|-------------|
| 0 | Config Resolution | Compile packet, load configs |
| 1 | Intent Analysis | Extract intent fields |
| 2 | Cinematic Enrichment | Choose color, lighting, lens |
| 3 | Scene Blueprint | Build lighting diagram |
| 3.1 | Prompt Package | Assemble categorized prompt |
| 4 | Self-Review | Find gaps, propose fixes |
| 4.1 | Cleanup | Deduplicate, fix contradictions |
| 4.2 | Renderer | Select model, convert syntax |
| 4.3 | Delivery | Normalize field names |
| 5 | Output | Format final prompt pack |

Some phases (0, 3, 3.1, 4.1, 4.2, 4.3, 5) auto-complete with deterministic
Python logic — the harness fills the response and continues immediately.

Phases 1, 2, and 4 require an LLM response. The harness prints
`[HARNESS WAITING]`, writes the prompt, and exits. You write a
`response_phase_N.json` matching the schema, then resume:

For a named fictional character, the harness runs
`scripts/resolve_adult_character.py --query <name>` automatically during
Phase 1 after receiving the intent response.

### Resume example

```bash
# First run
python3 scripts/harness.py --request "clearly adult cosplay of Tifa Lockhart" --outdir /tmp/harness-tifa
# → [HARNESS WAITING] Phase: phase_1_intent_analysis
# → Write /tmp/harness-tifa/response_phase_1_intent_analysis.json

# Resume
python3 scripts/harness.py --resume /tmp/harness-tifa
# → After phase_1_intent_analysis, auto-completes phases 3, 3.1
# → [HARNESS WAITING] Phase: phase_2_composition_and_cinematography
```

## Quality Non-Regression Gate

Before promoting a catalog or leaf-module migration, compare the legacy and
candidate execution packets using `scripts/validate_quality_gate.py`. The
candidate must retain every legacy required claim and source leaf, reduce total
agent-visible context by at least 60%, reduce Phase-0 inline context by at
least 25%, and pass a paired manual ComfyUI benchmark with no lower score in
existing categories. Local anatomy and focus/camera scores must be at least
3/5. Do not exchange visual quality for a smaller context packet.

## Enhancement Pipeline

Follow `config/enhancement-pipeline.yaml` in order. Do not skip phases because
the request is NSFW or because Z-Image uses a different syntax.
For every request, classify the subject kind and resolve the always-NSFW
baseline before neutral intent, wardrobe preservation, or edit locks are
interpreted.

1. **Config resolution** — route every relevant visual and adult-safety module.
2. **Intent analysis** — extract hard locks, adult tier, subject identity,
   action, wardrobe state, edit scope, visual goal, crop, output size, and the
   internal dynamic-scene plan.
3. **Composition and cinematography** — resolve story goal, visual hierarchy,
   pose/action timing, camera relationship, shot scale, crop safety, gaze/action
   flow, frame layout, background role, negative space, depth layers, light
   hierarchy, and balance.
4. **Scene blueprint** — make pose support, body mechanics, contact anchors,
   force direction, occlusion, secondary motion, lighting behavior, material
   response, and environment physically coherent.
5. **Prompt package and review** — preserve intent; review anatomy, identity,
   scene readability, composition, material plausibility, and drift risks.
6. **Cleanup** — remove only redundancy and contradictions. Never remove a
   meaningful composition, crop, identity, action, wardrobe, or adult-content
   lock merely to shorten the prompt.
7. **Z-Image rendering** — render through `config/comfyui-prompt-pack.yaml`.
8. **Delivery validation** — validate the three output fields, adult boundary,
   English prompt text, preservation locks, and resolution.

### Authoritative Phase Ledger

The numbered summary above is descriptive only. The authoritative execution
order is the ten IDs in `config/execution-catalog.yaml` and the compiler packet:
`phase_0_config_resolution`, `phase_1_intent_analysis`,
`phase_2_composition_and_cinematography`, `phase_3_scene_blueprint`,
`phase_3_1_prompt_package`, `phase_4_self_review`, `phase_4_1_cleanup`,
`phase_4_2_comfyui_renderer`, `phase_4_3_delivery_package`, and
`phase_5_final_output`. Marking a phase complete without every packet-required
node, claim, and provenance mapping is invalid; the validator rejects it.

## Adult Eligibility

Before any visual enrichment, enforce `config/adult-content-policy.yaml`:

- Every subject must be clearly adult.
- Every named fictional character must have one unique whitelist match.
- Reject minor, age-ambiguous, youth-coded sexualized, and real-person-likeness
  requests before generating a prompt.
- Preserve the requested adult content tier after eligibility passes.
- Adult specialization never replaces composition, visual hierarchy, anatomy,
  lighting, material, or self-review rules.

### Always-NSFW Baseline

For every accepted human or humanoid subject, resolve the adult NSFW baseline
before ordinary intent interpretation.

When the user specifies clothing, retain its type, colour, signature design,
and identity markers, but resolve concrete physical opening, lowering,
pull-aside, displacement, or partial removal.

When clothing is unspecified, check for explicit nude keywords (全裸, 裸體,
不穿, nude, naked, fully nude). If any nude keyword is present, start the scene
with unmistakably full nude presentation. If no nude keyword is present,
randomly select a revealing NSFW outfit variant from `config/nsfw-outfit-library.yaml`.
If a variant trigger matches the prompt text, prefer that variant. Inject the
selected variant's anchors into the wardrobe specification as a
partial-nudity revealing outfit.

Requests for conservative, fully covered, or nonsexual presentation do not
disable this product baseline. Age safety and real-person blocking remain
higher priority.

### Visible Exposure Contract

For every eligible human/humanoid packet, resolve and record
`visible_exposure_contract` from `nsfw-visible-exposure-contract.yaml`.
Unspecified wardrobe with nude trigger keywords requires `full_nudity_required`;
unspecified wardrobe without nude trigger requires `auto_outfit` →
`partial_nudity_required` via a revealing NSFW outfit variant; explicit wardrobe
requires `partial_nudity_required` plus a concrete garment transformation.
For female/feminine subjects, select `nipple` or `vulva` as the visible evidence
target. Direct bare visibility is valid. A sheer or wet-fabric route is valid
only when that selected target is clearly visible—not merely suggested by a
contour, translucency, or body curve.

Keep the target in frame, unobscured, and readable. Hands, intact opaque
coverage, darkness, steam, shallow focus, or crop cannot hide the only target.
State the resolved exposure, evidence target, and garment action early in both
positive prompts. Add only the corresponding targeted Z-Image negative controls.
The validator rejects missing evidence, full coverage, vague transparency, or a
camera plan that loses the target. Nonhuman-only packets do not create this
contract.

### Exposure Action and Recovery

For each eligible human/humanoid scene, resolve exactly one primary exposure
target by default, then use `nsfw-exposure-action-controller.yaml` to bind it
to a route, garment zone, physical action, anchor, exposed/discernible end
state, and camera proof. A nipple target uses an upper-body action; a vulva
target uses a lower-body action. Do not use cleavage, a few opened buttons, or
generic wetness as a substitute for the required end state.

Use direct garment action, direct bare presentation, or a wet/translucent route.
The mixed router may introduce a scene-compatible moisture source, but a sheer
route must specify that source, clinging/stretch, light relation, and a target
that is actually discernible. Phase 4 must test target/action/end-state/camera
feasibility. Recompose from Phase 2 at most twice; if no route passes, block
delivery instead of returning a covered prompt.

For every exposure scene, record `exposure_geometry_plan` in
`camera_normalized_v1`: camera position/forward vector, target center/surface
normal/projected point, crop bounds, all limb/garment/prop occluder primitives,
and garment-action anchor/reach radius. At Phase 4, run
`scripts/check_exposure_geometry.py --packet ... --record ...`. Trace the
camera-to-target ray: the surface must face camera, the ray must be clear, the
action must reach the target, and projection must remain inside crop. This
checks the recorded scene plan—not final pixels. Store its structured result in
`exposure_geometry_result`; any failure requires up to two Phase-2
recompositions before delivery is blocked.

## Dynamic Scene and Surface Quality

Use `nsfw-dynamic-scene-controller.yaml` for every human scene. Establish the
pose family, motion state, action axis, support points, contact anchors, force
direction, occlusion order, gaze/reaction, secondary motion, and camera
readability before wording the prompt. For duo scenes, all participants are
clearly adult and the scene is consensual; assign a lead action and a readable
response rather than independent poses.

Use `nsfw-material-environment-controller.yaml` whenever surface state matters.
Wetness, steam, fabric tension, compression, reflection, and contact shadows
need a visible physical cause. Use `nsfw-composition-lighting-controller.yaml`
to keep faces, action/contact, support, material response, and environment in
priority order. Never use darkness, blur, steam, or foreground particles to hide
unsupported anatomy or contact.

Use `nsfw-visual-director.yaml` before generic visual-hierarchy rules. Unless
the user specifies another focus, give the sensory or readable interaction zone
the primary focus and use face/gaze as the secondary emotional read. Select one
camera relationship, shot scale, focal plane, crop, and occlusion order that
make this hierarchy visible. It supports clearly adult single and consensual-duo
private, fictional-public, POV, and BDSM contexts; do not route group scenes.

Use `nsfw-local-anatomy-surface-controller.yaml` only when a visible adult chest
surface is relevant to the crop, focus, material state, contact, pose, or light.
Resolve local form orientation, individual variation, gravity, fabric interface,
and key-light response as one surface system. Do not use mirrored, sticker-like,
floating, over-saturated, or cutout-like local anatomy; do not force a close-up
when the area is not part of the intended image.

Default to `cinematic_photoreal`. Switch to anime-realism only when the user
explicitly asks; translate materials into controlled stylized value groups and
highlights while retaining the same gravity, contact, occlusion, and support
logic.

## Edit Requests

For a reference/image edit, use `config/image-edit-policy.yaml` and the restored
edit-reference modules. For an eligible human source, validate first, apply the
adult-nude or transformed-wardrobe baseline, then make the requested edit.
After adultization, explicitly preserve identity, body proportions, pose,
camera, composition, scene, and every non-target attribute. A nonhuman source
keeps the existing edit-only behavior. Use the source dimensions or aspect ratio
for Suggested Resolution when known.

## Output Format

Return exactly this shape unless the user asks for a rationale:

```text
## Z-Image Final Positive Prompt
<English, detailed Z-Image prompt with the same enhanced scene>

## Z-Image Final Negative Prompt
<English, targeted failure controls that do not negate requested content>

## Suggested Resolution
<width>x<height> (<aspect ratio>)
```

For eligible human scenes, the Z-Image positive prompt must begin with the
resolved clearly-adult nude or transformed-wardrobe baseline. Z-Image receives
targeted negative terms only and must not negate the resolved adult baseline. Use explicit size first,
then explicit aspect ratio, then source image size/aspect ratio for edits, then
composition orientation.

## Pitfalls & CLI Quirks

### compile_execution_packet.py: --request vs --input

The compiler uses `--request`, NOT `--input`, for inline text input. Passing
inline text via `--input` makes the script treat it as a file path and crash
with `FileNotFoundError`. Correct usage:

```bash
python3 scripts/compile_execution_packet.py \
  --request "your prompt here" \
  --output /tmp/packet.json
```

### compiled_context inspection is a list, not a dict

When reading the packet JSON via Python, `compiled_context` is always a **list**
of node dicts (not a dict keyed by node_id). Each node has `node_id`, `claims`,
`sources`, and `content`. At Phase 0, `content` is empty (0 chars) — deferred
sources materialize only when their declared phase runs via
`materialize_execution_phase.py`. To inspect nodes:

```python
import json
p = json.load(open('/tmp/packet.json'))
ctx = p.get('compiled_context', [])  # LIST, not dict
for node in ctx:
    print(node['node_id'], len(node.get('content', '')))
```

### Phase materialization returns empty for many phases

Phases 0, 3, 4.1, 4.2, and 4.3 consistently return `sources: []` — the data
is already in `compiled_context`. Only Phase 2 (core-knowledge + visual-cinematography)
and Phase 3.1 (prompt-assembly-schema.yaml) load new deferred refs. This is by design,
not a bug.

## Strict Execution Patterns (Agent Pitfalls)

### Strict Mode — Every Phase Needs a Visible Record

Every phase must have a visible execution record — even when materialize
returns `sources: []`, the agent must still explicitly parse and document all
configs loaded at Phase 0, resolve every contract field, build the full ledger
with provenance for each claim, and only then assemble output. Empty
materialize sources ≠ empty work.

### When Materialize Returns Empty Sources (Expected)

| Phase | Why Empty | What You Must Still Do |
|-------|-----------|----------------------|
| `phase_0_config_resolution` | No prior phases to materialize | Read core-knowledge.yaml and _manifest.yaml; classify features; activate correct RuleNodes |
| `phase_1_intent_analysis` | All data in compiled_context from Phase 0 | Explicitly parse all always_load + conditional configs; classify subject_kind, resolve baseline, build exposure contract, extract hard locks — document every decision with config provenance |
| `phase_3_scene_blueprint` | Blueprint assembled from Phase 2 decisions | Build the full model-neutral blueprint: adult_baseline_tier, wardrobe_transformation, visible_exposure_contract, exposure_action_plan, exposure_geometry_plan, dynamic_scene_plan, local_anatomy_surface_contract, material_environment_plan, lighting_environment_plan — each with config source citations |
| `phase_4_2_comfyui_renderer` | Renderer logic in comfyui-prompt-pack.yaml (loaded Phase 0) | Apply Z-Image positive/negative assembly per comfyui-prompt-pack.yaml §z_image section; translate all blueprint fields into model-specific output |
| `phase_5_final_output` | Final = agent assembles from all prior phases | Return the three-field English prompt pack; include phase ledger if user asks for verification |

### Strict Mode Checklist (Every Phase)

1. Run `materialize_execution_phase.py --packet <path> --phase <name>`
2. If sources returned: read and fully parse each source YAML
3. If no sources returned: explicitly state why, then proceed with configs already loaded at Phase 0
4. For every decision made, cite the config file + section that justifies it
5. Build a visible ledger showing which claims were applied in this phase
6. Only after all phases complete → assemble final output

### Named Character Resolution Pitfall

When the user names a character (e.g., "Tifa Lockhart"), always check `config/adult-character-whitelist/index.yaml` first. If the name appears, it's whitelisted and eligible for NSFW baseline. If not found, either use `scripts/resolve_adult_character.py --query <name>` or reject before rendering — do NOT infer adulthood from context.

## Optional Export

Do not write files by default. Only when the user explicitly requests a file and
provides an absolute path, use `scripts/export_prompt_pack.py` with the strict
three-field JSON schema.
