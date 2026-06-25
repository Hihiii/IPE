# NSFW ComfyUI Cinematic Prompt Enhancer

An AI-agent skill that retains the original Cinematic Prompt Enhancer's
composition, camera, lighting, material, scene, anatomy, and quality-review
architecture while applying an always-NSFW adult baseline to eligible human
subjects for Z-Image workflows in ComfyUI.

**Version:** 3.6.0 | **License:** MIT | **Python:** >= 3.11

---

## Project Structure

```
.
├── SKILL.md                  # Agent-facing skill definition (primary execution guide)
├── config/
│   ├── _manifest.yaml        # Master manifest with triggers & loading rules
│   ├── execution-catalog.yaml# Authoritative phase/rule-node catalog
│   ├── core-knowledge.yaml   # Consolidated knowledge base (always-loaded)
│   ├── adult-content-policy.yaml
│   ├── prompt-core/          # Prompt assembly, review, quality rubric
│   ├── visual-cinematography/# Camera, lighting, composition rules (27 files)
│   ├── scene-environment/    # World-building, physics, atmosphere
│   ├── character-identity/   # Anatomy, pose, garment physics
│   ├── safety-mature/        # Mature-content tiering & guardrails
│   ├── edit-reference/       # Image edit & repair policies
│   └── skill-phase-*.yaml    # Phase-specific configs (loaded JIT)
├── scripts/                  # Python execution harness & utilities
├── tests/                    # Pytest suite (YAML contract + regression)
├── docs/                     # Execution runtime guide, benchmark sheet
├── references/               # Supporting reference materials
└── pyproject.toml
```

---

## What Is Preserved

The project still uses the original enhancement architecture:

- intent and hard-lock analysis;
- visual hierarchy, camera relationship, shot scale, crop safety, layout,
  negative space, depth, lighting, and visual-balance decisions;
- cinematic camera/lens/exposure/material knowledge;
- scene construction, contact physics, adult pose support, anatomy, fabric, and
  wetness plausibility;
- model-neutral prompt packaging, self-review, failure taxonomy, and cleanup;
- localized reference/image edits with preservation locks.

NSFW is a specialization layer, not a replacement for cinematic prompt quality.
The active pipeline is defined in [`SKILL.md`](SKILL.md) and
[`config/execution-catalog.yaml`](config/execution-catalog.yaml).

---

## Scope

- Text-to-image and reference/image edit requests.
- Clearly adult fictional/original human or humanoid subjects only.
- Every accepted human/humanoid prompt receives an adult-nude baseline, even
  when the input has no NSFW language.
- Explicit adult intent is preserved when requested.
- Nonhuman-only, object-only, and landscape-only requests remain non-NSFW.
- Outputs: Z-Image Final Positive Prompt, Z-Image Final Negative Prompt, and
  Suggested Resolution.
- Single and duo (consenting-adult) scenes only.

The skill rejects minors, age-ambiguous subjects, youth-coded sexualization, and
identifiable real-person likenesses. Named characters must resolve uniquely in
the adult whitelist. It does not create a ComfyUI workflow JSON or output final
prompts for non-Z-Image models.

---

## Quick Start

```bash
# Install dependencies
pip install PyYAML>=6.0

# Run a request through the harness
python3 scripts/harness.py --request "a mid 20s jpop idol just woke up with a lazy expression" --outdir /tmp/harness-work/
```

The harness pauses at LLM phases (1, 2, 4) with `[HARNESS WAITING]` — write a
`response_phase_N.json` matching the printed schema, then resume:

```bash
python3 scripts/harness.py --resume /tmp/harness-work/
```

### Run Tests

```bash
pip install ".[dev]"    # installs pytest
pytest                  # full suite
pytest -m yaml          # YAML contract validation only
```

---

## Pipeline

The 10 phases run in strict order. Every phase follows the same mechanism:
write `prompt_{phase}.json` → resolve `response_{phase}.json` → write
`checkpoint_{phase}.json`. Some phases auto-complete with deterministic
Python logic; others require an LLM response.

| # | Phase |
|---|-------|
| 0 | Config Resolution |
| 1 | Intent Analysis |
| 2 | Composition & Cinematography |
| 3 | Scene Blueprint |
| 3.1 | Prompt Package |
| 4 | Self-Review |
| 4.1 | Cleanup |
| 4.2 | Renderer |
| 4.3 | Delivery |
| 5 | Final Output |

**Phase 0** — Config Resolution  
Load the rule nodes and domain modules triggered by the request's features.
Large phase-specific sources start as deferred references and materialize
only at their declared phase.

**Phase 1 — Intent Analysis**  
Classify the subject kind, resolve the always-NSFW adult-nude baseline,
the visible exposure contract, and one exposure action target and route
(direct bare or sheer/translucent). Named characters are resolved against
the adult whitelist automatically.

**Phase 2 — Composition & Cinematography**  
Select the visual focus, camera relationship, shot scale, crop safety,
depth layers, and lighting hierarchy. For eligible human subjects the
sensory zone or readable adult interaction zone is primary; the face
and gaze provide secondary narrative information.

**Phase 3 — Scene Blueprint → Prompt Package**  
Build a model-neutral scene blueprint covering pose, support, contact,
material, lighting, and environment, then compile it into categorized
prompt fields with provenance and hard-lock anchors.

**Phase 4 — Self-Review → Cleanup → Render → Delivery**  
Evaluate intent preservation, exposure target–action–end-state
feasibility, and composition readability; recompose from Phase 2 at
most twice if needed. Remove redundancy and contradictions, format
for the Z-Image output contract, and deliver the validated three-field prompt
pack.

**Phase 5 — Final Output**  
Return Z-Image Final Positive Prompt, Z-Image Final Negative Prompt, and
Suggested Resolution.

---

## Quality Gate

Before deploying config or script changes, run the quality non-regression gate:

```bash
python3 scripts/validate_quality_gate.py --legacy <packet_a> --candidate <packet_b>
```

The candidate must retain every legacy required claim, reduce agent-visible
context by ≥60%, and pass a paired manual ComfyUI benchmark with no score
regression. See [`SKILL.md`](SKILL.md) for the full gate checklist.

---

## Agent Execution

This is an **AI-agent skill** designed for use with opencode and compatible
agent frameworks. For detailed execution instructions, phase contracts, strict
mode requirements, and common pitfalls, refer to [`SKILL.md`](SKILL.md) — the
primary agent-facing instruction set.

Key agent rules:
- Always run the compiled packet through all 10 phases — never skip.
- Every phase requires a visible execution record; empty materialized sources
  do not mean empty work.
- Every decision must cite its config-file provenance.
- Do not write output files unless the user provides an absolute path.

---

## Example

Raw request:

```
a mid 20s jpop idol just woke up with a lazy expression
```

### Z-Image Final Positive Prompt

```
clearly adult female J-pop idol, mid 20s, short tousled bed hair,
sleepy half-lidded eyes with a soft lazy expression, bare upper body
fully exposed with nipples clearly visible and unobstructed,
reclining back against stacked pillows on a rumpled bed, soft warm
morning window light from camera left sculpting her face and torso,
loose white sheet gathered at her hips, medium close-up from a
slightly elevated angle, shallow depth of field with face and chest
in sharp focus, muted bedroom background with cool dawn light
filtering through sheer curtains, filmic color grade, natural skin
texture with warm fleshy highlights
```

### Z-Image Final Negative Prompt

```
deformed, bad anatomy, disfigured, malformed limbs, extra fingers,
mutated hands, fused fingers, missing limbs, ugly, poorly drawn
face, cloned face, disproportionate, extra limbs, gross anatomy,
poorly drawn hands, missing fingers, long neck, distorted face,
bad proportions, double head, extra head, low quality, worst
quality, blurry, grainy, low resolution, watermark, signature,
text, logo, bad composition, cropped, out of frame, cut off
```

### Suggested Resolution

```
1024x1536 (2:3)
```

The raw request says "jpop idol" and "lazy expression" without
mentioning wardrobe, pose, camera, lighting, or environment. The
enhancer resolves the always-NSFW baseline (adult nude, no garment
invented for an unspecified wardrobe), selects a reclining bed scene
with soft morning light, places the bare torso as the primary visual
focus with the face as secondary, and writes a complete cinematic
prompt that satisfies the visible exposure contract and composition
decision order.
