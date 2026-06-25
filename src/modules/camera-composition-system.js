export class CameraCompositionSystem {
  constructor() {
    this.name = "11_camera_composition_system";
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const taxonomy = capsule?.shot_taxonomy || {};
    const angles = capsule?.camera_angles || {};
    const compositions = capsule?.composition_layouts || [];

    return {
      shotScale: this._detectShotScale(raw, taxonomy),
      cameraAngle: this._detectAngle(raw, angles),
      lens: this._detectLens(raw, capsule),
      depthOfField: this._detectDof(raw, capsule),
      composition: this._detectComposition(raw, compositions),
      isSelfie: this._isSelfie(raw, capsule),
      cropGuards: capsule?.crop_guardrails || [],
    };
  }

  _detectShotScale(raw, taxonomy) {
    if (raw.includes("extreme close-up") || raw.includes("macro")) return "extreme_close_up";
    if (raw.includes("close-up") || raw.includes("closeup") || raw.includes("face shot")) return "close_up";
    if (raw.includes("medium close-up")) return "medium_close_up";
    if (raw.includes("medium shot") || raw.includes("waist up")) return "medium_shot";
    if (raw.includes("medium full") || raw.includes("knee up") || raw.includes("3/4")) return "medium_full";
    if (raw.includes("full body") || raw.includes("full-body") || raw.includes("full shot")) return "full_shot";
    if (raw.includes("wide shot") || raw.includes("wide-shot") || raw.includes("long shot")) return "wide_shot";
    if (raw.includes("extreme wide") || raw.includes("establishing")) return "extreme_wide";
    return "medium_close_up";
  }

  _detectAngle(raw, angles) {
    if (raw.includes("low angle") || raw.includes("from below") || raw.includes("worm")) return "low_angle";
    if (raw.includes("high angle") || raw.includes("from above") || raw.includes("bird")) return "high_angle";
    if (raw.includes("dutch") || raw.includes("tilted")) return "dutch";
    if (raw.includes("overhead") || raw.includes("top down") || raw.includes("top-down")) return "overhead";
    if (raw.includes("selfie")) return "selfie_perspective";
    return "eye_level";
  }

  _detectLens(raw, capsule) {
    if (raw.includes("wide angle") || raw.includes("wide-angle") || raw.includes("wide angle lens")) return "wide_angle";
    if (raw.includes("telephoto") || raw.includes("telephoto lens") || raw.includes("zoom")) return "telephoto";
    if (raw.includes("macro") || raw.includes("macro lens")) return "macro";
    return "standard";
  }

  _detectDof(raw, capsule) {
    if (raw.includes("deep focus") || raw.includes("everything in focus")) return "deep";
    if (raw.includes("shallow") || raw.includes("blurred background") || raw.includes("bokeh")) return "shallow";
    if (raw.includes("extreme shallow")) return "extreme_shallow";
    return "medium";
  }

  _detectComposition(raw, layouts) {
    if (raw.includes("centered") || raw.includes("center")) return "centered";
    if (raw.includes("symmetry") || raw.includes("symmetrical")) return "symmetry";
    if (raw.includes("leading lines") || raw.includes("leading-line")) return "leading_lines";
    if (raw.includes("negative space") || raw.includes("minimal")) return "negative_space";
    if (raw.includes("golden ratio") || raw.includes("golden spiral")) return "golden_ratio";
    return "rule_of_thirds";
  }

  _isSelfie(raw, capsule) {
    const selfieConfig = capsule?.selfie || {};
    return raw.includes("selfie") && selfieConfig.phone_prohibited !== false;
  }
}
