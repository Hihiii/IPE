export class Phase4Review {
  constructor(orchestrator) {
    this.orchestrator = orchestrator;
  }

  async execute(ctx) {
    this._evaluateIntentPreservation(ctx);
    this._evaluateExposureFeasibility(ctx);
    this._evaluateComposition(ctx);
    this._cleanup(ctx);
    this._render(ctx);
    this._deliver(ctx);
  }

  _evaluateIntentPreservation(ctx) {
    const intent = ctx.detectedIntent || {};
    const package_ = ctx.promptPackage || {};
    const warnings = [];

    if (!package_.subject_core) {
      warnings.push("Subject core is empty — intent may be lost");
    }

    if (intent.subjectType === "human" && !package_.pose_and_body) {
      warnings.push("Human subject detected but no pose description");
    }

    if (intent.taskType === "selfie" && ctx.composition?.cameraAngle !== "selfie_perspective") {
      warnings.push("Selfie task requires selfie perspective");
    }

    ctx.warnings = ctx.warnings || [];
    ctx.warnings.push(...warnings);
  }

  _evaluateExposureFeasibility(ctx) {
    const contract = ctx.detectedIntent?.exposureContract || {};
    const package_ = ctx.promptPackage || {};

    if (contract.bareAllowed && contract.visible !== "full_explicit") {
      ctx.warnings.push("Policy requires full_explicit exposure — overriding");
      ctx.detectedIntent.exposureContract.visible = "full_explicit";
    }

    if (contract.clothed_never_allowed !== false) {
      ctx.nudityEnforced = true;
    }
  }

  _evaluateComposition(ctx) {
    const comp = ctx.composition || {};

    if (!comp.shotScale) {
      ctx.warnings.push("No shot scale selected");
    }

    if (!comp.lightingSetup) {
      ctx.warnings.push("No lighting setup defined");
    }

    if (comp.isSelfie && comp.cameraAngle === "eye_level") {
      ctx.warnings.push("Selfie mode should use selfie_perspective angle");
      ctx.composition.cameraAngle = "selfie_perspective";
    }
  }

  _cleanup(ctx) {
    const pkg = ctx.promptPackage || {};

    for (const [key, val] of Object.entries(pkg)) {
      if (typeof val === "string" && val.length > 200) {
        pkg[key] = val.slice(0, 200).trim();
      }
    }

    const policy = ctx.policy?.policies?.wardrobe || {};
    if (policy.auto_fill_prohibited && !this._hasExplicitWardrobe(ctx)) {
      ctx.wardrobeAutoFillBlocked = true;
    }

    if (ctx.composition?.isSelfie && pkg.subject_core) {
      const phonePatterns = ["phone", "smartphone", "iphone", "camera phone", "mobile"];
      for (const pat of phonePatterns) {
        if (pkg.subject_core.toLowerCase().includes(pat)) {
          if (!ctx.rawPrompt.toLowerCase().includes(pat)) {
            ctx.warnings.push(`Phone prop detected in prompt package but not in original prompt — removing`);
            pkg.subject_core = this._removeWord(pkg.subject_core, pat);
          }
        }
      }
    }

    this._deduplicate(ctx);
  }

  _hasExplicitWardrobe(ctx) {
    const raw = ctx.rawPrompt.toLowerCase();
    const explicitTerms = [
      "wearing", "dressed in", "clothed in", "outfit", "costume",
      "dress", "shirt", "pants", "skirt", "jacket", "coat",
      "bikini", "lingerie", "underwear", "nude", "naked",
      "uniform", "suit", "gown", "robe",
    ];
    return explicitTerms.some((t) => raw.includes(t));
  }

  _removeWord(text, word) {
    const regex = new RegExp(`\\b${word}\\b,?\\s*`, "gi");
    return text.replace(regex, "").trim();
  }

  _deduplicate(ctx) {
    const pkg = ctx.promptPackage || {};
    const seen = new Set();
    for (const [key, val] of Object.entries(pkg)) {
      if (typeof val === "string" && seen.has(val)) {
        if (val.length > 10) {
          pkg[key] = "";
        }
      }
      if (typeof val === "string") seen.add(val);
    }
  }

  _render(ctx) {
    const pkg = ctx.promptPackage || {};
    const order = ctx.outputSchema?.field_order?.positive || Object.keys(pkg);
    const nudityEnforced = ctx.nudityEnforced || ctx.detectedIntent?.exposureContract?.clothed_never_allowed !== false;

    const positiveParts = [];
    for (const field of order) {
      if (pkg[field] && typeof pkg[field] === "string" && pkg[field].trim()) {
        positiveParts.push(pkg[field].trim());
      }
    }

    if (nudityEnforced) {
      const hasParts = positiveParts.some((p) =>
        /\b(nipple|vulva|pussy|genitalia|cunt|labia)\b/i.test(p)
      );
      if (!hasParts) {
        positiveParts.push("visible nipples, exposed vulva, bare pussy, unobstructed genitalia");
      }
      const hasRealism = positiveParts.some((p) =>
        /\b(realistic|natural|authentic|pore|photorealistic)\b/i.test(p)
      );
      if (!hasRealism) {
        positiveParts.push("realistic nude skin texture, natural body, authentic skin");
      }
    }

    const negativeParts = [];
    const negativeCapsules = ctx.loadedCapsules?.filter((c) => c.negative_guards) || [];
    for (const cap of negativeCapsules) {
      const guards = cap.negative_guards;
      if (Array.isArray(guards)) {
        for (const g of guards) {
          if (!negativeParts.includes(g)) negativeParts.push(g);
        }
      }
    }

    if (nudityEnforced) {
      const censorGuards = [
        "censor bar",
        "mosaic censorship",
        "pixelated genitalia",
        "blurred vulva",
        "covered nipples",
        "pubic hair cover",
        "modesty patch",
        "obstruction over genitalia",
        "pasties",
        "tape over nipples",
        "underwear covering vulva",
      ];
      for (const g of censorGuards) {
        if (!negativeParts.includes(g)) negativeParts.push(g);
      }
      const fakeGuards = [
        "uncanny valley nudity",
        "fake nude",
        "CGI nude body",
        "artificial breast",
        "unnatural body proportions",
        "plastic skin",
        "waxy skin",
        "airbrushed skin",
        "doll-like nude",
        "silicone skin texture",
      ];
      for (const g of fakeGuards) {
        if (!negativeParts.includes(g)) negativeParts.push(g);
      }
    }

    if (negativeParts.length === 0) {
      negativeParts.push(
        "deformed, bad anatomy, disfigured, poorly drawn face, extra limbs, cloned face",
        "blurry, low quality, compressed, jpeg artifacts, watermark, signature",
        "plastic skin, waxy skin, over-smoothed, airbrushed",
      );
    }

    ctx.finalPositivePrompt = positiveParts.join(", ");
    ctx.finalNegativePrompt = negativeParts.join(", ");

    if (ctx.finalPositivePrompt.length > 2048) {
      ctx.warnings.push("Positive prompt exceeds 2048 character limit — truncating");
      ctx.finalPositivePrompt = ctx.finalPositivePrompt.slice(0, 2045).trimEnd();
    }
    if (ctx.finalNegativePrompt.length > 1024) {
      ctx.warnings.push("Negative prompt exceeds 1024 character limit — truncating");
      ctx.finalNegativePrompt = ctx.finalNegativePrompt.slice(0, 1021).trimEnd();
    }
  }

  _deliver(ctx) {
    const intent = ctx.detectedIntent || {};
    const taskType = intent.taskType || "portrait";

    const resolutions = {
      portrait: "832x1216",
      selfie: "832x1216",
      cinematic: "1216x832",
      product: "1024x1024",
      fashion: "896x1152",
      full_body: "896x1152",
      environment: "1216x832",
      wide: "1216x832",
    };

    ctx.suggestedResolution = resolutions[taskType] || "832x1216";

    ctx.compactPositivePrompt = ctx.finalPositivePrompt?.length > 512
      ? ctx.finalPositivePrompt.slice(0, 509).trimEnd() + "..."
      : ctx.finalPositivePrompt;

    ctx.compactNegativePrompt = ctx.finalNegativePrompt?.length > 256
      ? ctx.finalNegativePrompt.slice(0, 253).trimEnd() + "..."
      : ctx.finalNegativePrompt;

    if (this.orchestrator.options.verbose) {
      console.log(`  [Phase 4] Positive length: ${ctx.finalPositivePrompt?.length || 0} chars`);
      console.log(`  [Phase 4] Negative length: ${ctx.finalNegativePrompt?.length || 0} chars`);
      console.log(`  [Phase 4] Resolution: ${ctx.suggestedResolution}`);
    }
  }
}
