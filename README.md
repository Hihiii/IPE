# IPE OpenCode — Agentic Visual Prompt RAG

A modular, knowledge-driven prompt generation pipeline for Z-Image. The system parses raw intent, retrieves domain-specific capsules, and assembles validated positive/negative prompt packs through a deterministic 10-phase pipeline.

## Pipeline Phases

| Phase | Stage | Description |
|-------|-------|-------------|
| 0 | Config Resolution | Load rule nodes and domain modules triggered by request features |
| 1 | Intent Analysis | Classify subject kind, exposure contract, action target and route |
| 2 | Composition & Cinematography | Select visual focus, camera relationship, shot scale, depth, lighting |
| 3 | Scene Blueprint → Prompt Package | Build model-neutral blueprint; compile into categorized prompt fields |
| 4 | Self-Review → Cleanup → Render → Delivery | Evaluate, deduplicate, format for Z-Image output contract |
| 5 | Final Output | Return positive, negative, and suggested resolution |

## Architecture

```
src/
  index.js                   # Entry point
  pipeline/                  # Phase orchestrators (0-5)
  modules/                   # 20 domain system modules
  knowledge/loader.js        # Capsule retriever
  utils/                     # Logger, capsule parser

knowledge/
  capsules/                  # Runtime compiled capsules (lightweight)
  full/                      # Full YAML sources (not fed to model)
    character-ip/            # Character identity database
  indexes/                   # Module, character, alias indexes

```

## Core Principles

- **Parse first, retrieve second.** Intent drives module selection.
- **Capsule before agent.** Runtime uses compiled capsules, not full YAML.
- **Policy before renderer.** Rule engine constrains output, not free model judgment.
- **Validate before delivery.** Quality checks, conflict resolution, consistency verification.
- Identity may default; costume never auto-applies.
- Selfie is a perspective, not a phone prop.
- Undefined clothing slots are never auto-filled.
- Adult content is governed by explicit policy; youth-coded content is a hard guard.

## Usage

```bash
npm start -- --prompt "A woman standing in the rain, wet hair, city street at night"
```
