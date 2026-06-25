---
name: nsfw-comfyui-zimage-cinematic-prompt-enhancer
description: Prompt-only Agentic Visual Prompt RAG runtime for eligible adult NSFW cinematic Z-Image prompt packs. Use for adult prompt enhancement, prompt-pack validation, and phase-level runtime debugging.
---

# NSFW ComfyUI Z-Image Cinematic Prompt Enhancer

Use this skill to enhance eligible adult prompts into a strict three-field
Z-Image prompt pack. The project runtime source of truth is the `ipe` package.

## Direct Workflow

1. Eligibility
   - Accept clearly adult fictional, original, generic, or confirmed adult
     human/humanoid subjects.
   - Reject minors, youth-coded subjects, age-ambiguous sexualized subjects,
     and identifiable real-person NSFW requests.
   - Leave nonhuman-only, object-only, and landscape-only prompts non-NSFW.

2. Adult baseline
   - For eligible adult human/humanoid subjects, apply a clearly adult NSFW
     baseline.
   - Preserve user locks: identity, pose, setting, style, wardrobe identity,
     aspect ratio, exact text, and requested camera/composition.
   - Do not hide required adult presentation with crop, blur, darkness,
     foreground clutter, opaque coverage, or vague styling.

3. Cinematic enrichment
   - Add professional camera, shot scale, crop safety, lens behavior, lighting,
     exposure, color grade, material response, pose mechanics, contact/support,
     scene depth, and atmosphere.
   - Default to cinematic photoreal unless the user explicitly asks for another
     style.

4. Z-Image output
   - Output English prompt text.
   - Use targeted negative terms only.
   - Return exactly:

```text
## Z-Image Final Positive Prompt
<English detailed Z-Image prompt>

## Z-Image Final Negative Prompt
<English targeted failure controls>

## Suggested Resolution
<width>x<height> (<aspect ratio>)
```

## Runtime CLI

Use `ipe` when the user asks to run, inspect, debug, validate, or benchmark the
project runtime:

```bash
ipe run --request "prompt" --json
ipe inspect --request "prompt" --json
ipe run --request "prompt" --json --session /absolute/session
ipe phase --session /absolute/session --phase phase_2_composition_and_cinematography
ipe validate --session /absolute/session
ipe benchmark --cases tests/prompt-regression-cases.yaml --json
ipe capsules --validate
```

The runtime writes `request.json`, `intent_profile.json`, `module_plan.json`,
`capsule_plan.json`, `phase_ledger.json`, `capsule_access_log.json`,
`prompt_pack.json`, and `validation_report.json` for session runs.

Do not write output files unless the user explicitly requests a file path.
