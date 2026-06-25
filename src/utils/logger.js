const LEVELS = { silent: 0, error: 1, warn: 2, info: 3, debug: 4 };

export class Logger {
  constructor(level = "info") {
    this.level = LEVELS[level] ?? LEVELS.info;
  }

  error(...args) {
    if (this.level >= LEVELS.error) console.error("[ERROR]", ...args);
  }

  warn(...args) {
    if (this.level >= LEVELS.warn) console.warn("[WARN]", ...args);
  }

  info(...args) {
    if (this.level >= LEVELS.info) console.log("[INFO]", ...args);
  }

  debug(...args) {
    if (this.level >= LEVELS.debug) console.log("[DEBUG]", ...args);
  }
}

export const defaultLogger = new Logger("info");
