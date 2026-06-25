export class Phase2Composition {
  constructor(orchestrator) {
    this.orchestrator = orchestrator;
  }

  async execute(ctx) {
    const raw = ctx.rawPrompt.toLowerCase();
    const cameraCapsule = this._getCapsule(ctx, "camera-composition-system.capsule.yaml");
    const lightingCapsule = this._getCapsule(ctx, "lighting-exposure-system.capsule.yaml");

    ctx.composition = {
      shotScale: this._detectShotScale(raw, cameraCapsule),
      cameraAngle: this._detectAngle(raw, cameraCapsule),
      lensChoice: this._detectLens(raw, cameraCapsule),
      depthOfField: this._detectDof(raw, cameraCapsule),
      lightingSetup: this._detectLighting(raw, lightingCapsule),
      exposurePriority: this._detectExposure(raw, lightingCapsule),
      compositionLayout: this._detectLayout(raw, cameraCapsule),
      isSelfie: this._isSelfie(raw),
    };

    if (ctx.composition.isSelfie) {
      ctx.composition.cameraAngle = "selfie_perspective";
    }

    if (ctx.detectedIntent.subjectType === "human") {
      ctx.composition.sensoryZone = "primary";
      ctx.composition.faceGazePriority = "secondary_narrative";
    }

    ctx.depthLayers = {
      foreground: this._inferForeground(raw),
      subject: ctx.rawPrompt,
      background: this._inferBackground(raw),
    };

    if (this.orchestrator.options.verbose) {
      console.log(`  [Phase 2] Shot: ${ctx.composition.shotScale}, Angle: ${ctx.composition.cameraAngle}`);
      console.log(`  [Phase 2] Lighting: ${ctx.composition.lightingSetup}`);
    }
  }

  _detectShotScale(raw, capsule) {
    const taxonomy = (capsule.shot_taxonomy || {});
    if (raw.includes("close-up") || raw.includes("closeup") || raw.includes("macro")) return "close_up";
    if (raw.includes("medium shot") || raw.includes("medium-shot") || raw.includes("waist")) return "medium_shot";
    if (raw.includes("full body") || raw.includes("full-body")) return "full_shot";
    if (raw.includes("wide shot") || raw.includes("wide-shot") || raw.includes("environment")) return "wide_shot";
    if (raw.includes("extreme wide")) return "extreme_wide";
    return "medium_close_up";
  }

  _detectAngle(raw, capsule) {
    if (raw.includes("low angle") || raw.includes("low-angle") || raw.includes("from below")) return "low_angle";
    if (raw.includes("high angle") || raw.includes("high-angle") || raw.includes("from above") || raw.includes("bird")) return "high_angle";
    if (raw.includes("dutch") || raw.includes("tilted")) return "dutch";
    if (raw.includes("overhead") || raw.includes("top down") || raw.includes("top-down")) return "overhead";
    if (raw.includes("selfie") || raw.includes("selfie-perspective") || raw.includes("self")) return "selfie_perspective";
    return "eye_level";
  }

  _detectLens(raw, capsule) {
    if (raw.includes("wide angle") || raw.includes("wide-angle")) return "wide_angle";
    if (raw.includes("telephoto") || raw.includes("zoom")) return "telephoto";
    if (raw.includes("macro")) return "macro";
    return "standard";
  }

  _detectDof(raw, capsule) {
    if (raw.includes("deep focus") || raw.includes("deep-focus")) return "deep";
    if (raw.includes("shallow") || raw.includes("blurred background") || raw.includes("bokeh")) return "shallow";
    if (raw.includes("extreme shallow")) return "extreme_shallow";
    return "medium";
  }

  _detectLighting(raw, capsule) {
    const setups = (capsule.lighting_setups || {});
    if (raw.includes("golden hour") || raw.includes("sunset") || raw.includes("sunrise")) return "natural_golden_hour";
    if (raw.includes("studio") || raw.includes("beauty dish") || raw.includes("softbox")) return "studio";
    if (raw.includes("cinematic") || raw.includes("film") || raw.includes("movie")) return "cinematic";
    if (raw.includes("night") || raw.includes("moonlight") || raw.includes("dark")) return "night";
    if (raw.includes("neon") || raw.includes("street light")) return "night_neon";
    if (raw.includes("backlit") || raw.includes("back light") || raw.includes("rim light")) return "backlit";
    if (raw.includes("fantasy") || raw.includes("magic") || raw.includes("glow")) return "fantasy";
    if (raw.includes("natural") || raw.includes("window light") || raw.includes("daylight")) return "natural";
    return "natural";
  }

  _detectExposure(raw, capsule) {
    if (raw.includes("high key") || raw.includes("bright") || raw.includes("overexposed")) return "high_key";
    if (raw.includes("low key") || raw.includes("dark") || raw.includes("shadowy")) return "low_key";
    if (raw.includes("backlit")) return "backlit";
    if (raw.includes("night") || raw.includes("moonlight")) return "readable_night";
    return "standard";
  }

  _detectLayout(raw, capsule) {
    if (raw.includes("centered") || raw.includes("center")) return "centered";
    if (raw.includes("symmetry") || raw.includes("symmetrical")) return "symmetry";
    if (raw.includes("rule of thirds")) return "rule_of_thirds";
    if (raw.includes("negative space") || raw.includes("minimal")) return "negative_space";
    if (raw.includes("leading lines") || raw.includes("leading-line")) return "leading_lines";
    return "rule_of_thirds";
  }

  _isSelfie(raw) {
    return raw.includes("selfie") && !raw.includes("non-selfie") && !raw.includes("not selfie");
  }

  _inferForeground(raw) {
    if (raw.includes("foreground")) return raw.match(/foreground[^.]*\.?/i)?.[0] || "";
    return "";
  }

  _inferBackground(raw) {
    if (raw.includes("background")) return raw.match(/background[^.]*\.?/i)?.[0] || "";
    return "";
  }

  _getCapsule(ctx, name) {
    return this.orchestrator.knowledgeLoader.parser.load(name);
  }
}
