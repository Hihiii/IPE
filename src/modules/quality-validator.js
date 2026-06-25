export class QualityValidator {
  constructor() {
    this.name = "19_quality_failure_validation";
  }

  process(ctx, capsule) {
    const checklist = capsule?.quality_checklist || {};
    const failures = [];
    const recomposeRequired = false;

    if (checklist.intent_preservation) {
      const intent = ctx.detectedIntent || {};
      if (!intent.taskType) {
        failures.push({ rule: "intent_preservation", severity: "critical", message: "No task type detected" });
      }
    }

    if (checklist.composition_readability) {
      if (!ctx.composition?.shotScale) {
        failures.push({ rule: "composition", severity: "high", message: "No shot scale defined" });
      }
    }

    if (checklist.physical_coherence) {
      if (ctx.sceneBlueprint?.pose && !ctx.sceneBlueprint?.support) {
        failures.push({ rule: "physical_coherence", severity: "high", message: "Pose without support definition" });
      }
    }

    if (checklist.lighting_consistency) {
      if (!ctx.composition?.lightingSetup) {
        failures.push({ rule: "lighting", severity: "medium", message: "No lighting setup defined" });
      }
    }

    const warnings = [];
    for (const f of failures) {
      if (f.severity === "critical") {
        warnings.push(`[CRITICAL] ${f.message}`);
      } else if (f.severity === "high") {
        warnings.push(`[HIGH] ${f.message}`);
      }
    }

    const repairPlan = this._buildRepairPlan(failures, capsule);

    return {
      qualityScore: Math.max(0, 100 - failures.length * 15),
      failures,
      repairPlan,
      recomposeRequired,
      warnings,
    };
  }

  _buildRepairPlan(failures, capsule) {
    const taxonomy = capsule?.failure_taxonomy || {};
    return failures.map((f) => {
      const action = taxonomy[f.rule]?.action || "add_guardrails";
      return { field: f.rule, action };
    });
  }
}
