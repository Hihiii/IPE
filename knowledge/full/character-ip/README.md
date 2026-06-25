# Character IP Database

## Structure

```
character-ip/
  _global/          # Cross-IP shared definitions
  _indexes/         # Master character index files
  anime/            # Anime IP characters
  games/            # Game IP characters
  manga/            # Manga IP characters
  mixed-media/      # Vocaloid, original characters, etc.
```

## Per-Character Files

Each character has a dedicated folder with:

- `identity.yaml`         - Canonical name, aliases, source, role
- `appearance.yaml`       - Visual summary and key traits
- `face-hair-body.yaml`   - Detailed facial structure, hair system, body type
- `outfits/canonical.yaml` - Canonical outfit description (trigger-only)
- `props-weapons.yaml`    - Signature items
- `pose-language.yaml`    - Characteristic poses and stances
- `expression-gaze.yaml`  - Signature expressions and eye behavior
- `color-palette.yaml`    - Locked color scheme
- `world-motifs.yaml`     - Associated environment themes
- `prompt-pack.yaml`      - Pre-built prompt fragments
- `negative-guards.yaml`  - What must not drift
- `validation.yaml`       - Identity verification rules

## Policy

- Identity may be used by default when a character is named.
- Costume is NEVER auto-applied unless canonical/cosplay trigger is present.
- All visual traits are hard-locked against drift.
