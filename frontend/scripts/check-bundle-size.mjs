// Bundle-size gate: fails CI when a built chunk regresses past budget or
// when a heavy library (cornerstone, chart.js) leaks back into a chunk it
// does not belong to. Budgets are set ~10% above the current build so the
// gate catches regressions without flaking on minor variance.
import { readFileSync, readdirSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const assetsDir = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",
  "dist",
  "assets",
);

const MAX_CHUNK_GZIP = 1100 * 1024; // vendor-cornerstone is ~985 kB gzip
// baseline 2.26 MB incl. cornerstone computeWorker (~760 kB); raised to 2.5
// MB after R05 QA pages (QA queue/incidents/actions + antd icons) landed
const MAX_TOTAL_GZIP = 2.5 * 1024 * 1024;
const REQUIRED_CHUNKS = ["vendor-cornerstone", "vendor-chart"];

let failed = false;
let total = 0;
const chunks = [];

for (const file of readdirSync(assetsDir)) {
  if (!file.endsWith(".js")) continue;
  const bytes = readFileSync(join(assetsDir, file));
  const gzip = gzipSync(bytes).length;
  total += gzip;
  chunks.push({ file, gzip });
}

for (const required of REQUIRED_CHUNKS) {
  if (!chunks.some((c) => c.file.includes(required))) {
    failed = true;
    console.error(`FAIL: expected chunk "${required}" is missing — a manualChunks rule may have been dropped`);
  }
}

for (const { file, gzip } of chunks) {
  if (gzip > MAX_CHUNK_GZIP) {
    failed = true;
    console.error(`FAIL: ${file} is ${(gzip / 1024).toFixed(0)} kB gzip (limit ${MAX_CHUNK_GZIP / 1024} kB)`);
  }
}

console.log(
  `bundle: ${chunks.length} js chunks, ${(total / 1024 / 1024).toFixed(2)} MB gzip total`,
);
if (total > MAX_TOTAL_GZIP) {
  failed = true;
  console.error(`FAIL: total ${(total / 1024 / 1024).toFixed(2)} MB exceeds ${MAX_TOTAL_GZIP / 1024 / 1024} MB gzip`);
}

process.exit(failed ? 1 : 0);
