import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export class CapsuleParser {
  constructor(knowledgeDir) {
    this.knowledgeDir = knowledgeDir;
    this.capsuleCache = new Map();
  }

  load(capsuleName) {
    if (this.capsuleCache.has(capsuleName)) {
      return this.capsuleCache.get(capsuleName);
    }
    const path = resolve(this.knowledgeDir, "capsules", capsuleName);
    try {
      const raw = readFileSync(path, "utf-8");
      const parsed = this._parse(raw, capsuleName);
      this.capsuleCache.set(capsuleName, parsed);
      return parsed;
    } catch (err) {
      throw new Error(`Failed to load capsule "${capsuleName}": ${err.message}`);
    }
  }

  _parse(yamlText, source) {
    const lines = yamlText.split("\n");
    const result = {};
    const stack = [{ obj: result, indent: -1 }];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trimEnd();

      if (trimmed.trim() === "" || trimmed.trim().startsWith("#")) continue;

      const indent = line.length - trimmed.length + (trimmed.match(/^\s+/) ? 0 : 0);
      const content = trimmed.trim();
      const actualIndent = line.length - line.trimStart().length;

      if (content.startsWith("- ")) {
        const listItem = content.slice(2);
        const parent = this._findParent(stack, actualIndent);
        if (!parent._list) parent._list = [];
        parent._list.push(listItem);
        continue;
      }

      const colonIdx = content.indexOf(":");
      if (colonIdx === -1) continue;

      const key = content.slice(0, colonIdx).trim();
      const val = content.slice(colonIdx + 1).trim();

      while (stack.length > 1 && stack[stack.length - 1].indent >= actualIndent) {
        stack.pop();
      }

      const parent = stack[stack.length - 1].obj;

      if (val === "") {
        const newObj = {};
        parent[key] = newObj;
        stack.push({ obj: newObj, indent: actualIndent });
      } else {
        parent[key] = val;
      }
    }

    this._postProcess(result);
    return result;
  }

  _findParent(stack, indent) {
    for (let i = stack.length - 1; i >= 0; i--) {
      if (stack[i].indent < indent) return stack[i].obj;
    }
    return stack[0].obj;
  }

  _postProcess(obj) {
    for (const [key, val] of Object.entries(obj)) {
      if (val && typeof val === "object" && val._list) {
        const list = val._list;
        delete val._list;
        if (Object.keys(val).length === 0) {
          obj[key] = list;
        } else {
          val.items = list;
        }
      }
      if (val && typeof val === "object") {
        this._postProcess(val);
      }
    }
  }

  clearCache() {
    this.capsuleCache.clear();
  }
}
