import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

export class CharacterIPResolver {
  constructor(knowledgeDir) {
    this.name = "16_character_ip_database";
    this.knowledgeDir = knowledgeDir;
    this.characterIndex = null;
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const index = this._loadCharacterIndex();
    const matchedCharacters = [];

    if (index?.characters) {
      for (const [alias, [canonicalName, category, subfolder]] of Object.entries(index.characters)) {
        if (raw.includes(alias.toLowerCase())) {
          matchedCharacters.push({
            alias,
            canonicalName,
            category,
            subfolder: resolve(this.knowledgeDir, "full", "character-ip", subfolder),
          });
        }
      }
    }

    const hasCostumeTrigger = this._hasCostumeTrigger(raw, capsule);

    return {
      matchedCharacters,
      identityCanBeUsed: matchedCharacters.length > 0,
      costumeAutoApplied: false,
      costumeTriggered: hasCostumeTrigger,
      characterGuards: this._getCharacterGuards(matchedCharacters),
    };
  }

  _loadCharacterIndex() {
    if (this.characterIndex) return this.characterIndex;
    const indexPath = resolve(this.knowledgeDir, "indexes", "character-index.yaml");
    if (!existsSync(indexPath)) return { characters: {} };
    try {
      const raw = readFileSync(indexPath, "utf-8");
      this.characterIndex = { characters: {} };
      const lines = raw.split("\n");
      let currentChar = null;
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("#") || trimmed === "") continue;
        const aliasMatch = trimmed.match(/^([\w_]+):\s*\[/);
        if (aliasMatch) {
          currentChar = aliasMatch[1];
          const rest = trimmed.slice(trimmed.indexOf("[") + 1, trimmed.lastIndexOf("]"));
          const parts = rest.split(",").map((s) => s.trim().replace(/"/g, ""));
          if (parts.length >= 3) {
            this.characterIndex.characters[currentChar] = parts;
          }
        }
      }
      return this.characterIndex;
    } catch {
      return { characters: {} };
    }
  }

  _hasCostumeTrigger(raw, capsule) {
    const triggers = capsule?.costume_triggers || ["canonical", "cosplay", "original_outfit", "source_accurate"];
    return triggers.some((t) => raw.includes(t));
  }

  _getCharacterGuards(matched) {
    if (matched.length === 0) return [];
    return [
      "character identity preserved",
      "eye color locked",
      "hair style locked",
      "skin tone locked",
    ];
  }
}
