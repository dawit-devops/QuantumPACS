import { describe, it, expect } from "vitest";
import {
  MODALITIES,
  isValidModality,
  normalizeModality,
  type Modality,
} from "../../common/modalities";

describe("canonical modalities (D1)", () => {
  it("has no duplicate entries", () => {
    expect(new Set(MODALITIES).size).toBe(MODALITIES.length);
  });

  it("includes all standard radiology modalities", () => {
    const required = ["CT", "MR", "PET", "DX", "US", "MG", "FL", "XA", "NM"];
    for (const m of required) {
      expect(MODALITIES).toContain(m);
    }
  });

  it("includes MRI as an alias for MR", () => {
    // ScheduleBoard historically uses "MRI" — it must be recognized
    expect(MODALITIES).toContain("MRI");
  });

  it("isValidModality recognizes all canonical values", () => {
    for (const m of MODALITIES) {
      expect(isValidModality(m)).toBe(true);
    }
  });

  it("isValidModality recognizes MRI alias", () => {
    expect(isValidModality("MRI")).toBe(true);
  });

  it("isValidModality rejects unknown values", () => {
    expect(isValidModality("ZZZ")).toBe(false);
    expect(isValidModality("")).toBe(false);
  });

  it("normalizeModality maps MRI to MR", () => {
    expect(normalizeModality("MRI")).toBe("MR");
  });

  it("normalizeModality passes through standard values", () => {
    expect(normalizeModality("CT")).toBe("CT");
    expect(normalizeModality("MR")).toBe("MR");
    expect(normalizeModality("PET")).toBe("PET");
  });

  it("normalizeModality uppercases lowercase input", () => {
    expect(normalizeModality("ct")).toBe("CT");
    expect(normalizeModality("mr")).toBe("MR");
  });
});
