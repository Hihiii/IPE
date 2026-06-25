export class PromptRenderer {
  constructor() {
    this.name = "18_prompt_renderer_system";
  }

  process(ctx, capsule) {
    const positiveFields = capsule?.assembly_order?.positive || [];
    const negativeFields = capsule?.assembly_order?.negative || [];
    const pkg = ctx.promptPackage || {};

    const positiveParts = positiveFields
      .map((field) => {
        const description = typeof field === "string" ? field : field.key || "";
        const content = pkg[description] || "";
        return typeof content === "string" ? content.trim() : "";
      })
      .filter((p) => p.length > 0);

    const negativeParts = [];
    const negativeCapsules = ctx.loadedCapsules?.filter((c) => c.negative_guards) || [];
    for (const cap of negativeCapsules) {
      const guards = cap.negative_guards;
      if (Array.isArray(guards)) {
        for (const g of guards) {
          if (typeof g === "string" && !negativeParts.includes(g)) {
            negativeParts.push(g);
          }
        }
      }
    }

    const rules = capsule?.format_rules || {};
    const maxTotal = rules.max_total_length || 2048;
    const delimiter = rules.delimiter || ", ";

    let positive = positiveParts.join(delimiter);
    if (positive.length > maxTotal) {
      positive = positive.slice(0, maxTotal - 3).trimEnd() + "...";
    }

    const negativeMax = 1024;
    let negative = negativeParts.join(delimiter);
    if (negative.length > negativeMax) {
      negative = negative.slice(0, negativeMax - 3).trimEnd() + "...";
    }

    return {
      positive,
      negative,
      fieldCount: positiveParts.length,
      negativeFieldCount: negativeParts.length,
    };
  }
}
