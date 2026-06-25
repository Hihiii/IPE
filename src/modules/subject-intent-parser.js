export class SubjectIntentParser {
  constructor() {
    this.name = "01_subject_intent_parser";
  }

  analyze(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const classifiers = capsule?.classifiers || {};

    return {
      taskType: this._classifyTask(raw, classifiers),
      subjectType: this._classifySubject(raw, classifiers),
      primaryFocus: this._detectFocus(raw),
      retrievalPlan: this._buildRetrievalPlan(raw, classifiers),
    };
  }

  _classifyTask(raw, classifiers) {
    const tasks = classifiers.task_types || [];
    for (const t of tasks) {
      if (raw.includes(t)) return t;
    }
    return "portrait";
  }

  _classifySubject(raw, classifiers) {
    const humanKw = ["woman", "man", "girl", "boy", "person", "character", "female", "male", "figure"];
    for (const kw of humanKw) {
      if (raw.includes(kw)) return "human";
    }
    return "human";
  }

  _detectFocus(raw) {
    if (raw.includes("full body")) return "full_body";
    if (raw.includes("upper body") || raw.includes("waist up")) return "upper_body";
    if (raw.includes("face") || raw.includes("closeup") || raw.includes("close-up") || raw.includes("portrait")) return "face";
    return "face";
  }

  _buildRetrievalPlan(raw, classifiers) {
    const routing = classifiers.retrieval_routing || {};
    const type = this._classifySubject(raw, classifiers);
    return routing[type] || [];
  }
}
