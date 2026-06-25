export class Phase3Blueprint {
  constructor(orchestrator) {
    this.orchestrator = orchestrator;
  }

  async execute(ctx) {
    const reqCapsules = this.orchestrator.knowledgeLoader.loadByModules(ctx.activeModules);
    ctx.loadedCapsules = reqCapsules;

    ctx.sceneBlueprint = {
      subject: this._buildSubjectCore(ctx),
      pose: this._buildPose(ctx),
      support: this._buildSupport(ctx),
      contact: this._buildContact(ctx),
      material: this._buildMaterials(ctx),
      lighting: ctx.composition.lightingSetup,
      environment: this._buildEnvironment(ctx),
      narrative: this._buildNarrative(ctx),
    };

    ctx.promptPackage = this._compilePromptPackage(ctx);

    if (this.orchestrator.options.verbose) {
      console.log(`  [Phase 3] Blueprint built with ${ctx.sceneBlueprint.subject ? "subject" : "no subject"}`);
      console.log(`  [Phase 3] Prompt package fields: ${Object.keys(ctx.promptPackage).length}`);
    }
  }

  _buildSubjectCore(ctx) {
    const intent = ctx.detectedIntent || {};
    const raw = ctx.rawPrompt;
    if (intent.subjectType === "human") {
      return { type: "human", descriptor: raw.split(/[,.]/)[0]?.trim() || raw };
    }
    return { type: intent.subjectType || "unknown", descriptor: raw };
  }

  _buildPose(ctx) {
    const raw = ctx.rawPrompt.toLowerCase();
    if (raw.includes("sitting") || raw.includes("sit") || raw.includes("seated")) return "seated";
    if (raw.includes("lying") || raw.includes("lying down") || raw.includes("reclining") || raw.includes("laying")) return "reclining";
    if (raw.includes("kneeling") || raw.includes("kneel")) return "kneeling";
    if (raw.includes("walking") || raw.includes("running") || raw.includes("moving")) return "action";
    return "standing";
  }

  _buildSupport(ctx) {
    const raw = ctx.rawPrompt.toLowerCase();
    if (raw.includes("chair") || raw.includes("bench") || raw.includes("sofa") || raw.includes("couch")) return "furniture";
    if (raw.includes("floor") || raw.includes("ground") || raw.includes("grass")) return "floor";
    if (raw.includes("bed") || raw.includes("mattress")) return "bed";
    if (raw.includes("wall")) return "wall";
    if (raw.includes("table") || raw.includes("desk")) return "surface";
    return "self_supported";
  }

  _buildContact(ctx) {
    const support = this._buildSupport(ctx);
    return { support, type: support === "self_supported" ? "none" : "surface_contact" };
  }

  _buildMaterials(ctx) {
    const raw = ctx.rawPrompt.toLowerCase();
    const materials = [];
    const materialRefs = {
      silk: "silk", satin: "silk", velvet: "silk",
      cotton: "cotton", linen: "cotton",
      leather: "leather",
      denim: "denim", jeans: "denim",
      lace: "lace",
      vinyl: "vinyl", latex: "vinyl",
      wool: "wool", knit: "wool", cashmere: "wool",
      mesh: "mesh", net: "mesh",
      metal: "metal", gold: "metal", silver: "metal", chain: "metal",
    };
    for (const [kw, mat] of Object.entries(materialRefs)) {
      if (raw.includes(kw)) materials.push(mat);
    }
    return materials;
  }

  _buildEnvironment(ctx) {
    const raw = ctx.rawPrompt.toLowerCase();
    if (raw.includes("beach") || raw.includes("coast") || raw.includes("ocean") || raw.includes("sea")) return "beach_coastal";
    if (raw.includes("city") || raw.includes("street") || raw.includes("urban") || raw.includes("alley")) return "urban_street";
    if (raw.includes("forest") || raw.includes("woods") || raw.includes("trees")) return "forest";
    if (raw.includes("room") || raw.includes("bedroom") || raw.includes("interior")) return "interior_room";
    if (raw.includes("studio") || raw.includes("photo studio")) return "studio";
    if (raw.includes("night") || raw.includes("dark")) return "night_scene";
    return "neutral_background";
  }

  _buildNarrative(ctx) {
    const raw = ctx.rawPrompt.toLowerCase();
    if (raw.includes("walking") || raw.includes("running") || raw.includes("action")) return { moment: "action_peak", type: "dynamic" };
    if (raw.includes("waiting") || raw.includes("standing")) return { moment: "still_frame", type: "static" };
    if (raw.includes("sitting") || raw.includes("resting")) return { moment: "candid", type: "resting" };
    if (raw.includes("looking") || raw.includes("staring") || raw.includes("watching")) return { moment: "portrait", type: "observing" };
    return { moment: "portrait", type: "static" };
  }

  _compilePromptPackage(ctx) {
    const comp = ctx.composition || {};
    const blueprint = ctx.sceneBlueprint || {};

    return {
      subject_core: ctx.rawPrompt,
      identity_markers: "",
      expression_and_gaze: "",
      hair: "",
      pose_and_body: blueprint.pose || "",
      skin_and_makeup: "natural nude skin, realistic skin texture with visible pores",
      wardrobe: this._extractWardrobe(ctx),
      lighting: comp.lightingSetup || "",
      environment: blueprint.environment || "",
      atmosphere: "",
      camera: `${comp.shotScale || "medium"} ${comp.lensChoice || "standard"} ${comp.cameraAngle || "eye_level"}`,
      composition: comp.compositionLayout || "",
      color: "",
      narrative: blueprint.narrative?.moment || "",
      technical: "photorealistic, highly detailed, natural nude body, authentic nude anatomy",
    };
  }

  _extractWardrobe(ctx) {
    const raw = ctx.rawPrompt;
    const clothingKeywords = [
      "dress", "skirt", "shirt", "top", "blouse", "pants", "jeans", "shorts",
      "jacket", "coat", "sweater", "hoodie", "bikini", "swimsuit", "lingerie",
      "underwear", "bra", "panties", "thong", "socks", "shoes", "heels", "boots",
      "sneakers", "hat", "cap", "glasses", "sunglasses", "mask", "gloves",
      "scarf", "tie", "belt", "bag", "purse", "backpack", "jewelry", "necklace",
      "rings", "bracelet", "watch", "collar", "choker", "stockings", "tights",
      "uniform", "costume", "kimono", "robe", "gown", "suit", "vest",
      "naked", "nude", "topless", "bottomless", "nude",
    ];

    const found = [];
    for (const kw of clothingKeywords) {
      if (raw.toLowerCase().includes(kw)) found.push(kw);
    }
    return found.length > 0 ? found.join(", ") : "";
  }
}
