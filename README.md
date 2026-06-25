# NSFW ComfyUI Cinematic Prompt Enhancer

AI-agent skill for enhancing prompts into adult-only NSFW cinematic Z-Image
prompt packs for ComfyUI. The skill keeps the cinematic prompt enhancer
architecture: intent analysis, visual hierarchy, camera, lighting, material,
scene construction, anatomy checks, prompt packaging, cleanup, and review.

Version: 3.6.0 | License: MIT | Python: >= 3.11

## Scope

- Supports text-to-image and reference/image edit requests.
- Applies an always-NSFW adult baseline to eligible adult human or humanoid subjects.
- Preserves stronger explicit adult intent when requested.
- Rejects minors, age-ambiguous subjects, and youth-coded sexualized subjects.
- Leaves nonhuman-only, object-only, and landscape-only prompts non-NSFW.
- Outputs only:
  - Z-Image Final Positive Prompt
  - Z-Image Final Negative Prompt
  - Suggested Resolution

## Project Layout

```text
SKILL.md                  Agent-facing lightweight skill guide
config/                   Prompt rules, policy contracts, catalogs, schemas
scripts/                  Optional harness, validators, and utilities
tests/                    Pytest contract and regression tests
docs/                     Runtime notes and benchmark material
pyproject.toml            Packaging and test configuration
```

## Install And Test

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m pytest -m yaml
```

## Agent Usage

Agents should read `SKILL.md` and use the compact direct workflow by default:
eligibility, always-NSFW baseline, cinematic enrichment, Z-Image render, and
self-check.

Do not run the harness for ordinary prompt enhancement unless the user asks for
validation artifacts or a phase-level debug trace.

## Optional Harness

The harness is retained for debugging and regression validation. It writes
resumable prompts, responses, checkpoints, status, and final execution records.

```bash
python scripts/harness.py --request "clearly adult fictional woman in a cinematic room" --outdir /tmp/harness-work
```

The harness pauses at LLM phases 1, 2, and 4 with `[HARNESS WAITING]`. Use the
`response_template` in the corresponding `prompt_phase_*.json`, write
`response_phase_*.json`, then resume:

```bash
python scripts/harness.py --resume /tmp/harness-work
```

Schema failures are recorded in `_status.json` with the failing JSON path,
schema path, error message, and expected fields or enum values when available.

## Runtime Utilities

```bash
python scripts/compile_execution_packet.py --request "prompt" --output /absolute/packet.json
python scripts/materialize_execution_phase.py --packet /absolute/packet.json --phase phase_1_intent_analysis
python scripts/validate_execution_record.py --packet /absolute/packet.json --record /absolute/execution_record.json
python scripts/validate_adult_whitelist.py
```

Before deploying catalog or rule changes, use the quality gate:

```bash
python scripts/validate_quality_gate.py --legacy /absolute/legacy.json --candidate /absolute/candidate.json
```
