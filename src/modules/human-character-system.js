export class HumanCharacterSystem {
  constructor() {
    this.name = "02_human_character_system";
  }

  describe(rawPrompt, capsule) {
    const maturity = capsule?.maturity || {};
    const layers = capsule?.description_layers || {};

    return {
      maturity: { default: maturity.default || "adult", minAge: maturity.min_visual_age || 22 },
      descriptionPriority: this._getPriority(rawPrompt, layers),
      identityRequired: false,
    };
  }

  _getPriority(raw, layers) {
    const priority = { face: true, eyes: true, hair: true };
    if (raw.includes("full body")) priority.body = true;
    if (raw.includes("pose") || raw.includes("gesture")) priority.personality = true;
    return priority;
  }
}
