export class PoseBodyLanguageSystem {
  constructor() {
    this.name = "06_pose_body_language_system";
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const categories = capsule?.pose_categories || {};

    let detectedPose = "standing";
    for (const [pose, config] of Object.entries(categories)) {
      if (raw.includes(pose)) {
        detectedPose = pose;
        break;
      }
    }

    return {
      pose: detectedPose,
      poseConfig: categories[detectedPose] || categories.standing,
      anatomyGuards: capsule?.anatomy_guardrails || [],
      handIntent: this._detectHandIntent(raw, capsule),
    };
  }

  _detectHandIntent(raw, capsule) {
    const handCategories = capsule?.hand_intent?.categories || [];
    for (const hc of handCategories) {
      if (raw.includes(hc)) return hc;
    }
    return "resting";
  }
}
