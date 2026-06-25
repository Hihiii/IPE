export class Phase0Config {
  constructor(orchestrator) {
    this.orchestrator = orchestrator;
  }

  async execute(ctx) {
    const policy = ctx.policy;

    const map = this.orchestrator.knowledgeLoader.getModuleMap();
    ctx.moduleMap = map.modules || {};
    ctx.activeModules = [];

    for (const [id, mod] of Object.entries(ctx.moduleMap)) {
      if (mod.triggers && mod.triggers.includes("always")) {
        ctx.activeModules.push(id);
      }
    }

    const semPri = this.orchestrator.knowledgeLoader.getSemanticPriority();
    ctx.semanticPriority = semPri;

    ctx.hardLocks = [];
    if (semPri.hard_locks) {
      ctx.hardLocks = Array.isArray(semPri.hard_locks)
        ? semPri.hard_locks
        : Object.keys(semPri.hard_locks);
    }

    ctx.resolutionDefaults = {
      defaultWidth: 832,
      defaultHeight: 1216,
    };

    ctx.recomposeCount = 0;
    ctx.recomposeRequested = false;

    if (this.orchestrator.options.verbose) {
      console.log(`  [Phase 0] Always-resident modules: ${ctx.activeModules.join(", ")}`);
      console.log(`  [Phase 0] Hard locks: ${ctx.hardLocks.join(", ")}`);
    }
  }
}
