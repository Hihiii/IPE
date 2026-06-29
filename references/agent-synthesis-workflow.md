# Agent-Driven Prompt Pack Synthesis

When the ipe pipeline is compiled but you need to produce final output directly (not via a single script), follow this workflow.

## When to Use This

- `resolve_adult_character.py --query <name>` returns `"matched": false` (alias not in whitelist)
- You want to verify each phase's config before producing output
- The packet was compiled but no delivery script is available or you need custom rendering

## Step-by-Step

### 1. Compile the Packet

```bash
echo '{"request": "<user prompt>"}' > /tmp/ipe_input.json
python3 scripts/compile_execution_packet.py --input /tmp/ipe_input.json --output /tmp/ipe_packet.json
```

### 2. Materialize Each Phase (in order)

Run `materialize_execution_phase.py` for each phase. Most phases return empty sources — the compiled_context already holds the data. **Only these phases load deferred config:**

| Phase | What Loads | Why |
|-------|-----------|-----|
| `phase_2_composition_and_cinematography` | core-knowledge.yaml, composition-decision-engine.yaml, camera-technical-router.yaml, shot-taxonomy.yaml, crop-safety-rules.yaml, visual-hierarchy-system.yaml | Core cinematography rules |
| `phase_3_1_prompt_package` | prompt-assembly-schema.yaml | Prompt assembly pipeline |
| `phase_4_self_review` | quality-rubric.yaml, failure-taxonomy.yaml, intent-preservation-review.yaml | Quality checks |

All other phases (0, 1, 3, 4.1, 4.2, 4.3, 5) return empty sources — design behavior, not a bug.

### 3. Load NSFW Configs (if adult subject)

Check `deferred_references` in the packet for items with `activate_when: ["adult_human_scene"]`. These load automatically at their declared phase if the feature is active. Verify by checking which configs appear under `node_id: "adult_policy_and_delivery"`:

- nsfw-dynamic-scene-controller.yaml
- nsfw-material-environment-controller.yaml
- nsfw-composition-lighting-controller.yaml
- nsfw-local-anatomy-surface-controller.yaml
- nsfw-visual-director.yaml
- nsfw-semantic-exposure-visibility.yaml

### 4. Synthesize the Prompt Pack

Read the loaded configs and produce output following `comfyui-prompt-pack.yaml` rules:

**Z-Image Base+Turbo positive order:**
1. Resolved adult NSFW baseline (clearly adult + nude/wardrobe state)
2. Visible exposure evidence (target name, garment action)
3. Semantic visibility clearance (hair, hands, garment edge, light/focus/crop)
4. Visual focus & camera intent
5. Adult subject identity
6. Action & scene context
7. Pose, support, contact
8. Composition & camera
9. Lighting, material, environment
10. Style

**Z-Image positive:** Same content, denser comma-separated format, with constructive semantic visibility clearance instead of negative prompt controls.

**Krea2 positive:** Same content in a more natural paragraph, with fewer internal labels and the same positive semantic visibility clearance.

### 5. Resolution Policy

Default to `1024x1536 (2:3 portrait)` unless user specifies otherwise or source image dimensions are known.

## Key Pitfalls

- **Character resolution failure is normal**: Many character names aren't in the whitelist. Fall back to generic adult female/male classification and preserve identity anchors from the prompt itself.
- **Empty sources ≠ error**: Most phases return `{"sources": [], "reference_access": []}` because data lives in compiled_context. Only phase 2 and phase 3.1 load deferred configs.
- **adult_human_scene trigger**: FEATURE_PATTERNS only fires when input contains "adult", "woman", "man", "human", "humanoid", "character", "person", "nude", or "nsfw". Terms like "tifa" alone may not trigger it — prefix with "clearly adult female..." if needed.
- **Positive-only delivery**: The final pack has no negative prompt. Hair, hand, garment-edge, atmosphere, light, focus, crop, anatomy, and material safeguards must be written as constructive positive states.
