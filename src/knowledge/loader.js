import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { CapsuleParser } from "../utils/capusle-parser.js";

export class KnowledgeLoader {
  constructor(knowledgeDir) {
    this.knowledgeDir = knowledgeDir;
    this.parser = new CapsuleParser(knowledgeDir);
    this.alwaysResident = [];
  }

  loadAlwaysResident() {
    const always = [
      "global-policy.capsule.yaml",
      "prompt-output-schema.capsule.yaml",
      "master-module-map.capsule.yaml",
      "semantic-priority.capsule.yaml",
    ];
    for (const cap of always) {
      this.alwaysResident.push(this.parser.load(cap));
    }
    return this.alwaysResident;
  }

  loadByModules(moduleIds) {
    const moduleIndex = this.parser.load("master-module-map.capsule.yaml");
    const moduleMap = moduleIndex.modules || {};
    const loaded = [];

    for (const id of moduleIds) {
      const entry = moduleMap[id];
      if (!entry) continue;
      const capsuleName = entry.capsule;
      if (!capsuleName) continue;
      try {
        loaded.push(this.parser.load(capsuleName));
      } catch (err) {
        console.warn(`[KnowledgeLoader] Could not load ${capsuleName}: ${err.message}`);
      }
    }

    return loaded;
  }

  getModuleMap() {
    return this.parser.load("master-module-map.capsule.yaml");
  }

  getPolicy() {
    return this.parser.load("global-policy.capsule.yaml");
  }

  getSemanticPriority() {
    return this.parser.load("semantic-priority.capsule.yaml");
  }

  getOutputSchema() {
    return this.parser.load("prompt-output-schema.capsule.yaml");
  }
}
