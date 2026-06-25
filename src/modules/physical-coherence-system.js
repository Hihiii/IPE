export class PhysicalCoherenceSystem {
  constructor() {
    this.name = "08_physical_coherence_system";
  }

  process(rawPrompt, capsule) {
    return {
      gravityEnabled: capsule?.gravity?.enabled !== false,
      contactRules: capsule?.contact?.rules || [],
      collisionGuards: capsule?.collision_guardrails || [],
      compressionRules: this._compressionRules(rawPrompt, capsule),
      waterInteraction: capsule?.water_interaction || {},
      windSettings: capsule?.wind || {},
    };
  }

  _compressionRules(raw, capsule) {
    const compression = capsule?.compression || {};
    const active = {};

    if (raw.includes("bed") || raw.includes("mattress") || raw.includes("couch") || raw.includes("sofa") || raw.includes("pillow")) {
      active.softSurfaces = compression.soft_surfaces || [];
    }
    if (raw.includes("floor") || raw.includes("ground") || raw.includes("table") || raw.includes("counter")) {
      active.hardSurfaces = compression.hard_surfaces || [];
    }

    return active;
  }
}
