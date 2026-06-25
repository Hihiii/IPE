export class ColorScienceSystem {
  constructor() {
    this.name = "12_color_science_system";
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const strategies = capsule?.color_strategies || {};
    const grades = capsule?.grade_styles || {};

    let detectedStrategy = "natural_true";
    for (const [strategy, config] of Object.entries(strategies)) {
      if (raw.includes(strategy)) {
        detectedStrategy = strategy;
        break;
      }
    }

    return {
      colorStrategy: detectedStrategy,
      temperature: this._detectTemperature(raw),
      gradeStyle: this._detectGrade(raw, grades),
      skinProtection: capsule?.skin_tone_protection || [],
      forbiddenDrift: capsule?.forbidden_color_drift || [],
    };
  }

  _detectTemperature(raw) {
    if (raw.includes("warm") || raw.includes("golden") || raw.includes("sunset") || raw.includes("sunrise")) return "warm";
    if (raw.includes("cool") || raw.includes("cold") || raw.includes("blue") || raw.includes("moonlight")) return "cool";
    if (raw.includes("mixed") || raw.includes("neon") || raw.includes("multicolor")) return "mixed";
    return "neutral";
  }

  _detectGrade(raw, grades) {
    for (const [grade, desc] of Object.entries(grades)) {
      const keywords = grade.split("_");
      if (keywords.some((k) => raw.includes(k))) return grade;
    }
    return "natural_true";
  }
}
