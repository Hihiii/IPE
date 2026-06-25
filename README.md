# Agentic Visual Prompt RAG Runtime

Prompt-only runtime for converting raw user prompts into validated Z-Image
prompt packs. The runtime uses a strict 10-phase Agentic Visual Prompt RAG
pipeline, compact module capsules, deterministic routing, and validation.

Version: 4.0.0 | License: MIT | Python: >= 3.11

## Scope

- Supports text-to-image prompt enhancement and parse-only image edit intent.
- Applies an always-NSFW baseline only to eligible adult human/humanoid subjects.
- Blocks minors, youth-coded subjects, age-ambiguous sexualized subjects, and
  identifiable real-person NSFW requests.
- Leaves nonhuman-only, object-only, and landscape prompts non-NSFW.
- Outputs only:
  - Z-Image Final Positive Prompt
  - Z-Image Final Negative Prompt
  - Suggested Resolution

## Project Layout

```text
ipe/                       New Agentic Visual Prompt RAG runtime and CLI
config/master-module-map.yaml
config/capsules/           Compact runtime capsules for the 20 module systems
config/                    Source YAML knowledge and policy contracts
scripts/                   Legacy validators, harness utilities, and helpers
tests/                     Pytest contract and runtime regression tests
docs/                      Runtime notes and benchmark material
SKILL.md                   Agent-facing skill guide
```

## Install And Test

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Runtime CLI

```bash
ipe run --request "25 year old jpop idol lying on sofa" --json
ipe inspect --request "25 year old jpop idol lying on sofa" --json
ipe run --request "25 year old jpop idol lying on sofa" --json --session /absolute/session
ipe phase --session /absolute/session --phase phase_2_composition_and_cinematography
ipe validate --session /absolute/session
ipe benchmark --cases tests/prompt-regression-cases.yaml --json
ipe capsules --validate
```

The standard JSON output contract is:

```json
{
  "z_image_positive_prompt": "...",
  "z_image_negative_prompt": "...",
  "suggest_resolution": "1024x1536 (2:3)"
}
```

Session runs write:

```text
request.json
intent_profile.json
module_plan.json
capsule_plan.json
phase_ledger.json
capsule_access_log.json
prompt_pack.json
validation_report.json
```

## Runtime Model

The main runtime is no longer the legacy harness. It is the `ipe` package:

1. `subject_intent_parser`
2. `module_router`
3. `capsule_retriever`
4. `phase_engine`
5. `prompt_renderer`
6. `validator`

Normal runs load only compact capsules from `config/capsules/`. Full YAML is
materialized only for phase-level debugging or validation.

The 10 phases are:

```text
phase_0_config_resolution
phase_1_intent_analysis
phase_2_composition_and_cinematography
phase_3_scene_blueprint
phase_3_1_prompt_package
phase_4_self_review
phase_4_1_cleanup
phase_4_2_z_image_renderer
phase_4_3_delivery_package
phase_5_final_output
```

## Legacy Utilities

The previous `scripts/harness.py` and existing validators remain available for
regression/debug work, but new runtime work should target `ipe`.
