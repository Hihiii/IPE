export class SensoryDetailSystem {
  constructor() {
    this.name = "15_sensory_detail_system";
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const categories = capsule?.sensory_categories || {};
    const activeSensory = [];

    for (const [category, subcategories] of Object.entries(categories)) {
      if (typeof subcategories === "object") {
        for (const [subKey, cues] of Object.entries(subcategories)) {
          if (raw.includes(subKey)) {
            activeSensory.push({
              category,
              trigger: subKey,
              cues: Array.isArray(cues) ? cues : [cues],
            });
          }
        }
      }
    }

    return {
      activeSensoryCues: activeSensory,
      materialSensation: this._detectMaterialSensation(raw, capsule),
      forbidden: capsule?.forbidden || [],
    };
  }

  _detectMaterialSensation(raw, capsule) {
    const sensations = capsule?.material_sensation || {};
    for (const [mat, sensation] of Object.entries(sensations)) {
      if (raw.includes(mat)) return { material: mat, sensation };
    }
    return null;
  }
}
