import { describe, it, expect } from "vitest";
import { applyWindowLevel } from "../technologist/SimulatedPreview";

describe("applyWindowLevel", () => {
  it("maps a value at the window center to mid-gray", () => {
    // window=300, level=50 → span [ -100, 200 ]; value 50 is the center.
    expect(applyWindowLevel(50, 300, 50)).toBe(128);
  });

  it("clamps values below the window to black", () => {
    expect(applyWindowLevel(-150, 300, 50)).toBe(0);
  });

  it("clamps values above the window to white", () => {
    expect(applyWindowLevel(250, 300, 50)).toBe(255);
  });

  it("scales linearly inside the window", () => {
    // span [0, 100] with window=100, level=50; 75 → 75% of 255.
    expect(applyWindowLevel(75, 100, 50)).toBe(191);
    expect(applyWindowLevel(25, 100, 50)).toBe(64);
  });

  it("returns the value unchanged for a non-positive window", () => {
    expect(applyWindowLevel(80, 0, 50)).toBe(80);
    expect(applyWindowLevel(80, -10, 50)).toBe(80);
  });

  it("is monotonic inside the window (brighter input → brighter output)", () => {
    const a = applyWindowLevel(100, 400, 40);
    const b = applyWindowLevel(200, 400, 40);
    expect(b).toBeGreaterThan(a);
  });
});
