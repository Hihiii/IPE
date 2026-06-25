import { KnowledgeLoader } from "../knowledge/loader.js";
import { Phase0Config } from "./phase0-config.js";
import { Phase1Intent } from "./phase1-intent.js";
import { Phase2Composition } from "./phase2-composition.js";
import { Phase3Blueprint } from "./phase3-blueprint.js";
import { Phase4Review } from "./phase4-self-review.js";
import { Phase5Output } from "./phase5-output.js";

export class PipelineOrchestrator {
  constructor(options) {
    this.options = options;
    this.knowledgeLoader = new KnowledgeLoader(options.knowledgeDir);
    this.phases = {
      0: new Phase0Config(this),
      1: new Phase1Intent(this),
      2: new Phase2Composition(this),
      3: new Phase3Blueprint(this),
      4: new Phase4Review(this),
      5: new Phase5Output(this),
    };
    this.context = {};
    this.maxRecomposeAttempts = 2;
  }

  async execute(rawPrompt) {
    this.context = { rawPrompt, options: this.options };

    this.context.alwaysResident = this.knowledgeLoader.loadAlwaysResident();
    this.context.policy = this.knowledgeLoader.getPolicy();
    this.context.semanticPriority = this.knowledgeLoader.getSemanticPriority();
    this.context.outputSchema = this.knowledgeLoader.getOutputSchema();

    for (let phase = 0; phase <= 5; phase++) {
      const phaseName = this._phaseName(phase);
      this._log(`Phase ${phase} — ${phaseName}`);

      await this.phases[phase].execute(this.context);

      if (this.context.recomposeRequested && phase >= 2) {
        this._log(`Recompose requested (attempt ${this.context.recomposeCount || 0})`);
        if ((this.context.recomposeCount || 0) < this.maxRecomposeAttempts) {
          this.context.recomposeCount = (this.context.recomposeCount || 0) + 1;
          phase = 1;
          this.context.recomposeRequested = false;
          continue;
        }
        this._log("Max recompose attempts reached, proceeding with current composition.");
        this.context.recomposeRequested = false;
      }
    }

    return this._buildFinalOutput();
  }

  _phaseName(num) {
    const names = [
      "Config Resolution",
      "Intent Analysis",
      "Composition & Cinematography",
      "Scene Blueprint",
      "Self-Review / Cleanup / Render / Delivery",
      "Final Output",
    ];
    return names[num] || `Phase ${num}`;
  }

  _log(msg) {
    if (this.options.verbose) {
      console.log(`  [Orchestrator] ${msg}`);
    }
  }

  _buildFinalOutput() {
    const ctx = this.context;
    return {
      final_positive_prompt: ctx.finalPositivePrompt || "",
      final_negative_prompt: ctx.finalNegativePrompt || "",
      suggested_resolution: ctx.suggestedResolution || "832x1216",
      compact_positive_prompt: ctx.compactPositivePrompt,
      compact_negative_prompt: ctx.compactNegativePrompt,
      detected_intent: ctx.detectedIntent || {},
      warnings: ctx.warnings || [],
      debug_json: ctx.debug || {},
    };
  }
}
