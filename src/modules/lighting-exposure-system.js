export class LightingExposureSystem {
  constructor() {
    this.name = "10_lighting_exposure_system";
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const setups = capsule?.lighting_setups || {};

    let detectedSetup = "natural";
    for (const [setup, config] of Object.entries(setups)) {
      if (raw.includes(setup) || (config.variants || []).some((v) => raw.includes(v))) {
        detectedSetup = setup;
        break;
      }
    }

    return {
      lightingSetup: detectedSetup,
      variants: setups[detectedSetup]?.variants || [],
      exposureStrategy: this._detectExposure(raw, capsule),
      highlightPolicy: capsule?.highlight_policy || [],
    };
  }

  _detectExposure(raw, capsule) {
    const strategies = capsule?.exposure_strategies || {};
    for (const [strategy, rules] of Object.entries(strategies)) {
      const keywords = strategy.split("_");
      if (keywords.some((k) => raw.includes(k))) return strategy;
    }
    return "standard";
  }
}
