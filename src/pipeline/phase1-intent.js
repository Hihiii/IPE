export class Phase1Intent {
  constructor(orchestrator) {
    this.orchestrator = orchestrator;
  }

  async execute(ctx) {
    const raw = ctx.rawPrompt.toLowerCase();
    const intentCapsule = this._getCapsule(ctx, "subject-intent-parser.capsule.yaml");

    const taskType = this._classifyTask(raw, intentCapsule);
    const subjectType = this._classifySubject(raw, intentCapsule);
    const exposureContract = this._resolveExposure(raw, ctx.policy);

    ctx.detectedIntent = {
      taskType,
      subjectType,
      primaryFocus: this._detectFocus(raw),
      exposureContract,
      nsfwBaseline: "adult_nude",
      visibleExposure: exposureContract.visible,
    };

    ctx.activeModules = this._addTriggeredModules(raw, ctx);

    if (ctx.detectedIntent.subjectType === "human") {
      ctx.detectedIntent.exposureTarget = this._detectExposureTarget(raw);
      ctx.detectedIntent.exposureRoute = this._detectExposureRoute(raw);
    }

    if (this.orchestrator.options.verbose) {
      console.log(`  [Phase 1] Task: ${taskType}, Subject: ${subjectType}`);
      console.log(`  [Phase 1] Exposure: ${JSON.stringify(exposureContract)}`);
      console.log(`  [Phase 1] Active modules: ${ctx.activeModules.length} total`);
    }
  }

  _classifyTask(raw, capsule) {
    const classifiers = capsule.classifiers || {};
    const tasks = classifiers.task_types || [];
    for (const t of tasks) {
      if (raw.includes(t)) return t;
    }
    return "portrait";
  }

  _classifySubject(raw, capsule) {
    const types = (capsule.classifiers && capsule.classifiers.subject_types) || [];
    const humanKeywords = ["woman", "man", "girl", "boy", "female", "male", "person", "character", "figure"];
    for (const kw of humanKeywords) {
      if (raw.includes(kw)) return "human";
    }
    const envKeywords = ["room", "street", "city", "beach", "forest", "mountain", "interior", "exterior", "landscape"];
    for (const kw of envKeywords) {
      if (raw.includes(kw)) return "environment";
    }
    return "human";
  }

  _detectFocus(raw) {
    if (raw.includes("full body") || raw.includes("full-body")) return "full_body";
    if (raw.includes("upper body") || raw.includes("upper-body")) return "upper_body";
    if (raw.includes("face") || raw.includes("portrait") || raw.includes("close-up") || raw.includes("closeup")) return "face";
    if (raw.includes("detail") || raw.includes("macro")) return "detail_shot";
    return "face";
  }

  _resolveExposure(raw, policy) {
    const pol = policy.policies || {};
    const contract = pol.exposure_contract || {};
    const result = {
      baseline: contract.nsfw_default || "always_nsfw",
      visible: "full_explicit",
      sheerAllowed: contract.sheer_translucent_allowed !== false,
      bareAllowed: contract.direct_bare_allowed !== false,
    };

    if (raw.includes("sheer") || raw.includes("translucent") || raw.includes("see-through") || raw.includes("see through")) {
      result.visible = "sheer_translucent";
    }

    return result;
  }

  _detectExposureTarget(raw) {
    const parts = [];
    if (raw.includes("nipple") || raw.includes("nipples")) parts.push("nipples");
    if (raw.includes("pussy") || raw.includes("vagina") || raw.includes("labia") || raw.includes("pubic")) parts.push("vulva");
    if (raw.includes("ass") || raw.includes("anus") || raw.includes("butt") || raw.includes("anal")) parts.push("anal");
    if (raw.includes("penis") || raw.includes("cock") || raw.includes("dick")) parts.push("penis");
    if (parts.length === 0) {
      parts.push("nipples", "vulva", "pussy");
    }
    return parts.join(", ");
  }

  _detectExposureRoute(raw) {
    if (raw.includes("sheer") || raw.includes("translucent") || raw.includes("see-through")) return "sheer_translucent";
    if (raw.includes("lift") || raw.includes("pull") || raw.includes("remove") || raw.includes("open") || raw.includes("expose")) return "reveal_action";
    return "fully_exposed_unobstructed";
  }

  _addTriggeredModules(raw, ctx) {
    const active = new Set(ctx.activeModules || []);

    for (const [id, mod] of Object.entries(ctx.moduleMap)) {
      const triggers = mod.triggers || [];
      for (const t of triggers) {
        if (t === "always") continue;
        if (raw.includes(t)) {
          active.add(id);
          break;
        }
      }
    }

    return Array.from(active);
  }

  _getCapsule(ctx, name) {
    return this.orchestrator.knowledgeLoader.parser.load(name);
  }
}
