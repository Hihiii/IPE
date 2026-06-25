import { PipelineOrchestrator } from "../src/pipeline/orchestrator.js";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const knowledgeDir = resolve(__dirname, "..", "knowledge");

async function runTest(description, prompt, expectedChecks) {
  const orchestrator = new PipelineOrchestrator({
    knowledgeDir,
    verbose: false,
    mode: "preview",
  });

  const result = await orchestrator.execute(prompt);
  const passed = expectedChecks.every((check) => check(result));

  console.log(`${passed ? "PASS" : "FAIL"}: ${description}`);
  if (!passed) {
    console.log(`  Prompt: "${prompt}"`);
    console.log(`  Positive: ${result.final_positive_prompt?.slice(0, 100)}...`);
    console.log(`  Negative: ${result.final_negative_prompt?.slice(0, 100)}...`);
  }

  return passed;
}

const checks = {
  hasPositive: (r) => r.final_positive_prompt?.length > 0,
  hasNegative: (r) => r.final_negative_prompt?.length > 0,
  hasResolution: (r) => !!r.suggested_resolution,
  noPhoneInSelfie: (r) => !r.final_positive_prompt?.toLowerCase().includes("phone"),
};

async function main() {
  let allPassed = true;

  allPassed &= await runTest(
    "Basic portrait",
    "A woman with red hair, green eyes, sitting in a chair",
    [checks.hasPositive, checks.hasNegative, checks.hasResolution],
  );

  allPassed &= await runTest(
    "Selfie mode without phone",
    "Selfie of a woman with wet hair after rain",
    [checks.hasPositive, checks.noPhoneInSelfie],
  );

  allPassed &= await runTest(
    "Atmospheric night scene",
    "A woman standing in the rain, city street at night, neon lights",
    [checks.hasPositive, checks.hasNegative],
  );

  allPassed &= await runTest(
    "Minimal prompt",
    "Portrait of a woman",
    [checks.hasPositive, checks.hasResolution],
  );

  console.log(`\n${allPassed ? "ALL TESTS PASSED" : "SOME TESTS FAILED"}`);
  process.exit(allPassed ? 0 : 1);
}

main().catch((err) => {
  console.error("Test suite error:", err);
  process.exit(1);
});
