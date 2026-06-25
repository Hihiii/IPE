export class PolicyRuleEngine {
  constructor() {
    this.name = "17_policy_rule_system";
  }

  process(ctx, capsule) {
    const raw = ctx.rawPrompt.toLowerCase();
    const policy = ctx.policy?.policies || {};
    const rules = capsule?.cleanup_rules || {};
    const warnings = [];

    const hardGuardActive = policy.youth_content?.hard_guard_active !== false;
    if (hardGuardActive) {
      const youthMarkers = ["teen", "teenager", "child", "underage", "minor", "adolescent", "young girl", "young boy", "youth", "loli", "shota"];
      for (const marker of youthMarkers) {
        if (raw.includes(marker)) {
          warnings.push(`HARD GUARD TRIGGERED: youth-coded marker "${marker}" detected. Policy violation.`);
        }
      }
    }

    const explicitWardrobe = policy.wardrobe?.auto_fill_prohibited !== false;
    if (explicitWardrobe) {
      const inferringContexts = ["rain", "beach", "room", "bedroom", "forest", "city", "street", "swimming", "pool", "ocean"];
      for (const ctx_ of inferringContexts) {
        if (raw.includes(ctx_)) {
          warnings.push(`Context "${ctx_}" does not authorize automatic clothing inference.`);
          break;
        }
      }
    }

    const selfiePolicy = policy.selfie?.default_perspective_only !== false;
    if (selfiePolicy && raw.includes("selfie")) {
      if (raw.includes("phone") || raw.includes("smartphone") || raw.includes("selfie stick")) {
        warnings.push("Selfie policy violation: phone prop prohibited in selfie perspective.");
      }
    }

    return {
      activePolicies: Object.keys(policy),
      cleanupRules: rules,
      warnings,
      hardGuards: this._collectHardGuards(policy),
    };
  }

  _collectHardGuards(policy) {
    const guards = [];
    if (policy.youth_content?.hard_guard_active) guards.push("no_youth_coded_content");
    if (policy.wardrobe?.auto_fill_prohibited) guards.push("no_wardrobe_auto_fill");
    if (policy.selfie?.phone_prop_prohibited) guards.push("no_phone_in_selfie");
    if (policy.character_ip?.costume_auto_apply === false) guards.push("no_auto_costume");
    return guards;
  }
}
