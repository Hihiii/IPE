export class HairPhysicsSystem {
  constructor() {
    this.name = "04_hair_physics_system";
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const physics = capsule?.physics || {};
    const guards = capsule?.negative_guards || [];
    const activePhysics = [];

    for (const [state, effects] of Object.entries(physics)) {
      if (raw.includes(state)) {
        activePhysics.push({ state, effects });
      }
    }

    return {
      activePhysics,
      negativeGuards: Array.isArray(guards) ? guards : [],
      identityLock: capsule?.hair_identity?.drift_protection === "hard_lock",
    };
  }
}
