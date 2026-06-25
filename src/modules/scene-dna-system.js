export class SceneDNASystem {
  constructor() {
    this.name = "13_scene_dna_system";
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const sceneTypes = capsule?.scene_types || {};

    let detectedScene = "interior";
    for (const [scene, config] of Object.entries(sceneTypes)) {
      if (raw.includes(scene)) {
        detectedScene = scene;
        break;
      }
    }

    const sceneConfig = sceneTypes[detectedScene] || {};

    return {
      sceneType: detectedScene,
      primaryMarkers: sceneConfig.markers || [],
      subType: this._detectSubType(raw, sceneConfig.sub_types || []),
      backgroundRole: this._detectBackgroundRole(raw, capsule),
      driftGuards: capsule?.forbidden_scene_drift || [],
    };
  }

  _detectSubType(raw, subTypes) {
    for (const st of subTypes) {
      if (raw.includes(st)) return st;
    }
    return subTypes[0] || "generic";
  }

  _detectBackgroundRole(raw, capsule) {
    const roles = capsule?.background_role || {};
    if (raw.includes("environment") || raw.includes("landscape") || raw.includes("wide")) return "primary";
    if (raw.includes("blurred background") || raw.includes("bokeh")) return "minimal";
    if (raw.includes("atmospheric") || raw.includes("moody")) return "atmospheric";
    return "supportive";
  }
}
