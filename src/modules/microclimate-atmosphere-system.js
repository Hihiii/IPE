export class MicroclimateAtmosphereSystem {
  constructor() {
    this.name = "09_microclimate_atmosphere_system";
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const weatherStates = capsule?.weather_states || {};
    const detectedWeather = [];

    for (const [weather, config] of Object.entries(weatherStates)) {
      if (raw.includes(weather)) {
        const intensity = this._detectIntensity(raw, config.intensity || []);
        detectedWeather.push({
          type: weather,
          intensity,
          effects: config.effects || [],
        });
      }
    }

    return {
      activeWeather: detectedWeather,
      environmentInteraction: this._getInteractions(raw, capsule),
    };
  }

  _detectIntensity(raw, intensities) {
    for (const i of intensities) {
      if (raw.includes(i)) return i;
    }
    return intensities[0] || "moderate";
  }

  _getInteractions(raw, capsule) {
    const interactions = capsule?.environment_interaction || {};
    const active = {};
    for (const [condition, effects] of Object.entries(interactions)) {
      const parts = condition.split("_");
      if (parts.some((p) => raw.includes(p))) {
        active[condition] = effects;
      }
    }
    return active;
  }
}
