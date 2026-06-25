---
name: nsfw-comfyui-zimage-cinematic-prompt-enhancer
description: Always-NSFW cinematic prompt enhancement for eligible adult fictional or original human/humanoid subjects, rendered as a three-field ComfyUI Z-Image prompt pack. Use when the user wants an adult NSFW prompt upgraded with professional camera, lighting, composition, anatomy, material, and scene direction.
---

# NSFW ComfyUI Z-Image Cinematic Prompt Enhancer

Enhance the user's prompt into a detailed adult NSFW cinematic Z-Image prompt
pack. Use the compact direct workflow by default. Use the harness only for
debugging, validation, or regression work.

## Direct Workflow

1. Eligibility
   - Accept clearly adult fictional, original, or generic human/humanoid subjects.
   - Reject minors, age-ambiguous subjects, and youth-coded sexualized subjects.
   - For named fictional characters, resolve adult eligibility with
     `scripts/resolve_adult_character.py --query "<name>"` when identity matters.
   - Leave nonhuman-only, object-only, and landscape-only prompts non-NSFW.

2. Always-NSFW baseline
   - For every eligible human/humanoid subject, apply a clearly adult NSFW
     baseline even when the user did not request NSFW wording.
   - Preserve explicit adult intent when the user asks for it.
   - If wardrobe is specified, preserve its identity markers while transforming
     it into a visibly NSFW state.
   - If wardrobe is unspecified, use a nude baseline when nude wording is
     present; otherwise select a revealing adult outfit variant from
     `config/nsfw-outfit-library/index.yaml`.

3. Cinematic enhancement
   - Preserve user hard locks: identity, pose, setting, exact text, outfit
     identity, aspect ratio, and requested style.
   - Add professional composition, camera relationship, lens behavior, crop,
     depth, lighting, exposure, color grade, material response, pose mechanics,
     and environment details.
   - Default to cinematic photoreal. Use anime-realism or illustration only when
     the user requests it.
   - Keep the adult focus readable; do not hide required adult presentation with
     darkness, steam, blur, foreground clutter, hands, opaque fabric, or crop.

4. Z-Image render
   - Produce English prompt text.
   - Begin the positive prompt with the resolved adult baseline.
   - Use targeted negative terms only; do not negate the adult baseline.
   - Choose resolution by explicit user size first, then aspect ratio, then
     source image size/aspect ratio for edits, then composition orientation.

5. Self-check
   - Confirm adult eligibility and reject state.
   - Confirm the prompt did not drift from user locks.
   - Confirm camera, crop, lighting, anatomy, material, and scene details support
     the requested image rather than generic NSFW wording.
   - Confirm the final answer contains only the three requested fields unless
     the user asks for rationale.

## Output Format

Return exactly:

```text
## Z-Image Final Positive Prompt
<English detailed Z-Image prompt>

## Z-Image Final Negative Prompt
<English targeted failure controls>

## Suggested Resolution
<width>x<height> (<aspect ratio>)
```

## Optional Harness

Use `scripts/harness.py` only when the user asks to debug, validate, or inspect
phase-level execution:

```bash
python scripts/harness.py --request "your prompt" --outdir /tmp/harness-work
python scripts/harness.py --resume /tmp/harness-work
```

The harness writes `prompt_phase_*.json`, includes a `response_template` for
manual LLM phases, validates `response_phase_*.json` against JSON Schema, writes
checkpoints, and records failures in `_status.json`.

Helpful utilities:

```bash
python scripts/compile_execution_packet.py --request "prompt" --output /absolute/packet.json
python scripts/materialize_execution_phase.py --packet /absolute/packet.json --phase phase_1_intent_analysis
python scripts/validate_execution_record.py --packet /absolute/packet.json --record /absolute/execution_record.json
python scripts/validate_adult_whitelist.py
```

Do not write output files unless the user explicitly requests a file path.
