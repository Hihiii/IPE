export class VisualNarrativeSystem {
  constructor() {
    this.name = "14_visual_narrative_system";
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const moments = capsule?.narrative_moments || {};
    const roles = capsule?.story_roles || {};

    let detectedMoment = "portrait";
    for (const [moment, desc] of Object.entries(moments)) {
      if (raw.includes(moment.replace(/_/g, " "))) {
        detectedMoment = moment;
        break;
      }
    }

    return {
      narrativeMoment: detectedMoment,
      momentDescription: moments[detectedMoment] || "",
      storyRole: this._detectRole(raw, roles),
      actionReason: raw.match(/(because|to|in order to|for)\s+\w+/i)?.[0] || "",
      propFunction: this._detectPropFunction(raw, capsule),
    };
  }

  _detectRole(raw, roles) {
    if (raw.includes("performing") || raw.includes("dancing") || raw.includes("singing") || raw.includes("posing")) return "performer";
    if (raw.includes("watching") || raw.includes("observing") || raw.includes("looking at")) return "observer";
    if (raw.includes("fighting") || raw.includes("running") || raw.includes("attacking")) return "participant";
    return "protagonist";
  }

  _detectPropFunction(raw, capsule) {
    const props = capsule?.prop_story_function || {};
    if (raw.includes("sword") || raw.includes("gun") || raw.includes("knife") || raw.includes("weapon")) return props.weapon || "implies_conflict_or_defense";
    if (raw.includes("book") || raw.includes("tool") || raw.includes("instrument")) return props.tool || "implies_activity";
    if (raw.includes("phone") || raw.includes("photo") || raw.includes("letter")) return props.personal_item || "implies_character_depth";
    return "";
  }
}
