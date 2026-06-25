# NSFW ComfyUI Cinematic Prompt Enhancer

An AI-agent skill that retains the original Cinematic Prompt Enhancer's
composition, camera, lighting, material, scene, anatomy, and quality-review
architecture while applying an always-NSFW adult baseline to eligible human
subjects for Flux and Z-Image workflows in ComfyUI.

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
The active pipeline is defined in
[`config/enhancement-pipeline.yaml`](config/enhancement-pipeline.yaml).

## Scope

- Text-to-image and reference/image edit requests.
- Clearly adult fictional/original human or humanoid subjects only.
- Every accepted human/humanoid prompt receives an adult-nude baseline, even
  when the input has no NSFW language.
- Explicit adult intent is preserved when requested.
- Nonhuman-only, object-only, and landscape-only requests remain non-NSFW.
- Flux Final Prompt, Z-Image Final Positive Prompt, Z-Image Final Negative
  Prompt, and Suggested Resolution.

The skill rejects minors, age-ambiguous subjects, youth-coded sexualization, and
identifiable real-person likenesses. Named characters must resolve uniquely in
the adult whitelist. It does not create a ComfyUI workflow JSON or output final
prompts for non-Flux/Z-Image models.

## Pipeline

Phase 0 — Config Resolution  
Load the rule nodes and domain modules triggered by the request's features.
Large phase-specific sources start as deferred references and materialize
only at their declared phase.

Phase 1 — Intent Analysis  
Classify the subject kind, resolve the always-NSFW adult-nude baseline,
the visible exposure contract, and one exposure action target and route
(direct bare or sheer/translucent).

Phase 2 — Composition & Cinematography  
Select the visual focus, camera relationship, shot scale, crop safety,
depth layers, and lighting hierarchy. For eligible human subjects the
sensory zone or readable adult interaction zone is primary; the face
and gaze provide secondary narrative information.

Phase 3 — Scene Blueprint → Prompt Package  
Build a model-neutral scene blueprint covering pose, support, contact,
material, lighting, and environment, then compile it into categorized
prompt fields with provenance and hard-lock anchors.

Phase 4 — Self-Review → Cleanup → Render → Delivery  
Evaluate intent preservation, exposure target–action–end-state
feasibility, and composition readability; recompose from Phase 2 at
most twice if needed. Remove redundancy and contradictions, format
for the Flux / Z-Image output contract, and deliver the validated
four-field prompt pack.

Phase 5 — Final Output  
Return Flux Final Prompt, Z-Image Final Positive Prompt, Z-Image Final
Negative Prompt, and Suggested Resolution.

## Example

Raw request:

```
a mid 20s jpop idol just woke up with a lazy expression
```

Result — Flux Final Prompt (after running through the pipeline above):

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

The raw request says "jpop idol" and "lazy expression" without
mentioning wardrobe, pose, camera, lighting, or environment. The
enhancer resolves the always-NSFW baseline (adult nude, no garment
invented for an unspecified wardrobe), selects a reclining bed scene
with soft morning light, places the bare torso as the primary visual
focus with the face as secondary, and writes a complete cinematic
prompt that satisfies the visible exposure contract and composition
decision order.
