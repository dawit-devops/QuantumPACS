import type { AxeResults } from "axe-core";
import axe from "axe-core";

// F3 (GAP_AUDIT_TDD_PIPELINE.md): WCAG 2.1 AA automated scans via axe-core
// under jsdom. jsdom lacks a layout engine, so color-contrast rules are
// excluded (they need real rendering) — the structural/name/role/label
// rules that jsdom CAN evaluate are what we gate on. Violations of the
// remaining rules fail the page scan.
const EXCLUDED_RULES = ["color-contrast", "target-size"];

export interface AxeScanOptions {
  excludeRules?: string[];
}

export async function scanA11y(
  container: HTMLElement,
  options: AxeScanOptions = {},
): Promise<AxeResults> {
  const exclude = [...EXCLUDED_RULES, ...(options.excludeRules ?? [])];
  return axe.run(container, {
    rules: { ...Object.fromEntries(exclude.map((id) => [id, { enabled: false }])) },
  });
}

export function seriousViolations(results: AxeResults) {
  return results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
}

export function formatViolations(violations: AxeResults["violations"]) {
  return violations
    .map(
      (v) =>
        `${v.id} (${v.impact}): ${v.help} — ${v.nodes.length} node(s), e.g. ${v.nodes[0]?.html ?? ""}`,
    )
    .join("\n");
}
