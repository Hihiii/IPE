# Controlled Execution Runtime

The runtime makes phase completion and YAML relevance auditable without adding
debug fields to the final ComfyUI prompt pack.

## Session Flow

1. Compile a request into an execution packet.
2. Give the agent only `compiled_context` and `execution_record_template`.
3. The agent completes every phase in order and records claims plus provenance.
4. Validate the record. Success prints the three Z-Image prompt-pack fields; failure
   writes a machine-readable trace in the system temporary directory unless a
   path is explicitly supplied.

```powershell
python scripts/compile_execution_packet.py --request "your prompt" --output C:\temp\packet.json
python scripts/validate_execution_record.py --packet C:\temp\packet.json --record C:\temp\record.json
```

`request.json` contains a natural-language request and optional conservative
feature hints. Hints can only expand the selected closure; they must not remove
features inferred from the request.

```json
{
  "request": "clearly adult original fictional woman in a wet white shirt",
  "features": ["material_or_environment_response"]
}
```

## Record Requirements

The record must use the compiler template unchanged for packet IDs and phase
order. Every phase requires `status: complete`, all packet-required node IDs,
phase claims, and provenance entries mapping each required claim to a selected
node and phase. Its `prompt_pack` must satisfy the existing strict exporter
schema.

## Harness Progress

Run the resumable harness with `python scripts/harness.py --request "..."`.
Interactive terminals receive a ten-phase progress bar on stderr; non-TTY
callers receive one JSON `harness_progress` event per state transition.
`_status.json` is the stable integration surface and includes `state`,
`current_phase`, `phase_index`, `phase_count`, `percent_complete`,
`waiting_for_input`, `elapsed_seconds`, `next_action`, and `error`.

When a phase needs an LLM response, the harness exits successfully in
`waiting_for_response` state. Write the named response file and resume with
`--resume`. Validation failures exit nonzero and leave `failure_trace.json` and
`execution_record.json` in the session directory.

## Quality Gate

Use a paired manual benchmark JSON after running identical workflow, model,
seed, resolution, and control inputs for legacy and candidate prompt packs.

```json
{
  "baseline_scores": {"composition_and_crop": 4},
  "candidate_scores": {"composition_and_crop": 4}
}
```

The complete score object must include every category listed in
`config/quality-contract.yaml`. The candidate retains all legacy required claims,
must reduce agent-visible context by at least 60%, cannot lower an existing
benchmark score, and must score at least 3/5 in every new category.
