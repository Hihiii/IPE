import { PipelineOrchestrator } from "./pipeline/orchestrator.js";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

function parseArgs() {
  const args = process.argv.slice(2);
  const flags = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith("--")) {
      const key = args[i].slice(2);
      const val = args[i + 1] && !args[i + 1].startsWith("--") ? args[i + 1] : true;
      flags[key] = val;
      if (val !== true) i++;
    }
  }
  return flags;
}

async function main() {
  const flags = parseArgs();
  const prompt = flags.prompt || flags.p || "";

  if (!prompt) {
    console.error("Usage: npm start -- --prompt \"your prompt here\"");
    process.exit(1);
  }

  const orchestrator = new PipelineOrchestrator({
    knowledgeDir: resolve(__dirname, "..", "knowledge"),
    verbose: flags.verbose || flags.v || false,
    mode: flags.mode || "preview",
  });

  console.log(`\n[IPE OpenCode] Processing prompt: "${prompt}"\n`);

  const result = await orchestrator.execute(prompt);

  console.log("\n=== PHASE 5 — FINAL OUTPUT ===\n");
  console.log("Z-Image Final Positive Prompt:");
  console.log(result.final_positive_prompt);
  console.log("\nZ-Image Final Negative Prompt:");
  console.log(result.final_negative_prompt);
  console.log("\nSuggested Resolution:");
  console.log(result.suggested_resolution);

  if (result.warnings && result.warnings.length > 0) {
    console.log("\nWarnings:");
    result.warnings.forEach((w) => console.log(`  - ${w}`));
  }

  return result;
}

main().catch((err) => {
  console.error("Pipeline failed:", err);
  process.exit(1);
});
