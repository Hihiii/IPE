export class Phase5Output {
  constructor(orchestrator) {
    this.orchestrator = orchestrator;
  }

  async execute(ctx) {
    const output = {
      final_positive_prompt: ctx.finalPositivePrompt || "",
      final_negative_prompt: ctx.finalNegativePrompt || "",
      suggested_resolution: ctx.suggestedResolution || "832x1216",
      compact_positive_prompt: ctx.compactPositivePrompt || "",
      compact_negative_prompt: ctx.compactNegativePrompt || "",
      detected_intent: ctx.detectedIntent || {},
      warnings: ctx.warnings || [],
    };

    ctx.finalOutput = output;

    if (this.orchestrator.options.verbose) {
      console.log(`  [Phase 5] Resolution: ${output.suggested_resolution}`);
    }
  }
}
