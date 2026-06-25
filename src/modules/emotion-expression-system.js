export class EmotionExpressionSystem {
  constructor() {
    this.name = "05_emotion_expression_system";
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const mapping = capsule?.mapping || {};
    const gaze = capsule?.gaze || {};

    let detectedEmotion = "neutral";
    for (const [emotion, descriptors] of Object.entries(mapping)) {
      if (raw.includes(emotion)) {
        detectedEmotion = emotion;
        break;
      }
    }

    return {
      emotion: detectedEmotion,
      expressionDescriptors: mapping[detectedEmotion] || mapping.neutral,
      gaze: this._detectGaze(raw, gaze),
      forbidden: capsule?.forbidden || [],
    };
  }

  _detectGaze(raw, gazeMap) {
    const gazeKeywords = Object.keys(gazeMap);
    for (const kw of gazeKeywords) {
      if (raw.includes(kw) || raw.includes(`gaze ${kw}`) || raw.includes(`looking ${kw}`)) {
        return { type: kw, description: gazeMap[kw] };
      }
    }
    return { type: "direct", description: gazeMap.direct || "confrontational_or_intimate" };
  }
}
