export class SkinRenderingSystem {
  constructor() {
    this.name = "03_skin_rendering_system";
  }

  process(rawPrompt, capsule, environment) {
    const raw = rawPrompt.toLowerCase();
    const guards = capsule?.negative_guards || [];
    const envResponse = capsule?.environment_response || {};
    const selectedEffects = [];

    for (const [condition, effects] of Object.entries(envResponse)) {
      if (raw.includes(condition)) {
        selectedEffects.push(...effects);
      }
    }

    return {
      textureQuality: "realistic",
      negativeGuards: Array.isArray(guards) ? guards : [],
      environmentEffects: selectedEffects,
      highlightControl: this._highlightStrategy(raw),
    };
  }

  _highlightStrategy(raw) {
    if (raw.includes("wet") || raw.includes("rain") || raw.includes("sweat")) return "wet_sheen";
    if (raw.includes("oily") || raw.includes("glossy")) return "high_specular";
    return "natural_diffuse";
  }
}
