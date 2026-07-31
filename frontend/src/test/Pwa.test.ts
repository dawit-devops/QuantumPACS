import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const configPath = resolve(import.meta.dirname, "../../vite.config.js");

describe("PWA scaffold", () => {
  it("vite config includes VitePWA plugin", () => {
    const config = readFileSync(configPath, "utf-8");
    expect(config).toContain("VitePWA");
    expect(config).toContain("'QuantumPACS'");
    expect(config).toContain("'standalone'");
    expect(config).toContain("'pwa-192x192.png'");
  });
});
