import { existsSync, readFileSync } from "node:fs";
import { basename, join } from "node:path";
import { test, expect, type Page } from "@playwright/test";
import { loginAsAdmin, API_BASE, BASE } from "./helpers";

// E2E: the DICOM viewer renders a real image end-to-end. The suite's other
// viewer specs treat the fixture as a DB row (no pixel data), so they cannot
// prove decode + paint; this one uploads a real DICOM through the backend
// API (idempotent by content hash — a re-run returns the existing file id),
// opens /files/{id}, and asserts the full pipeline: the loading overlay
// clears, the WW/WC readout reflects the decoded pixel data, and the WebGL
// canvas is actually painted with multi-shade content (not a cleared or
// blank buffer).
//
// Fixture: frontend/e2e/fixtures/fixture-ct-001.dcm — 256×256 16-bit CT,
// Explicit VR Little Endian (no codec dependency), with a brightness ramp +
// square + ring + dot so a canvas probe sees many distinct shades. WC 500 /
// WW 1399 are baked in so the readout assertion is deterministic.
//
// E2E_DICOM_PATH overrides the committed fixture with any real DICOM on
// disk — e.g. the 8.5 MB JPEG-Lossless ATIRA radiograph in DICOM/… — so the
// same render assertions run against production-style data. Uploads are
// content-hash idempotent either way, so re-runs reuse the same file row.
const DEFAULT_FIXTURE_PATH = join(__dirname, "fixtures", "fixture-ct-001.dcm");
const DICOM_PATH = process.env.E2E_DICOM_PATH || DEFAULT_FIXTURE_PATH;

// Committed compressed-transfer-syntax fixtures, generated synthetically:
// - fixture-jpeg-baseline.dcm: 8-bit JPEG Baseline (TS 1.2.840.10008.1.2.4.50),
//   Pillow-encoded stream wrapped with pydicom (no pydicom JPEG encoder exists
//   in 3.x, so the bitstream is produced directly).
// - fixture-jpeg-ls.dcm: 16-bit JPEG-LS Lossless (TS 1.2.840.10008.1.2.4.80),
//   CharLS-encoded via the installed @cornerstonejs/codec-charls wasm.
// Each exercises a different decoder the viewer's worker ships
// (codec-libjpeg-turbo-8bit and codec-charls respectively).
const COMPRESSED_FIXTURES: ReadonlyArray<[string, string]> = [
  ["fixture-jpeg-baseline.dcm", "JPEG-Baseline (TS 1.2.840.10008.1.2.4.50)"],
  ["fixture-jpeg-ls.dcm", "JPEG-LS (TS 1.2.840.10008.1.2.4.80)"],
];

/**
 * Uploads the DICOM under test (path, or the E2E_DICOM_PATH override /
 * committed fixture by default) via the same multipart endpoint the UI uses,
 * and returns the new file id. Callers must have logged in first — the
 * upload rides the context cookie jar (IAM H-2). Content-hash dedup makes
 * re-runs reuse the same row.
 */
async function uploadDicom(
  page: Page,
  path = DICOM_PATH,
): Promise<{ id: number }> {
  // Fail fast with an actionable message when an explicit E2E_DICOM_PATH is
  // wrong — a silent fallback would mask a typo'd path.
  if (!existsSync(path)) {
    throw new Error(
      `DICOM fixture '${path}' does not exist` +
        (process.env.E2E_DICOM_PATH ? " (set via E2E_DICOM_PATH)" : ""),
    );
  }

  // The backend returns {id, duplicate} (no envelope wrapper), and a
  // duplicate upload returns the existing row, so retries are safe.
  const upload = await page.request.post(`${API_BASE}/api/files/upload`, {
    // The app's api/client.ts sends this static header on every mutation;
    // the backend's CSRFMiddleware demands it for browser-driven routes.
    // Auth is the HttpOnly cookie from the login in the same context.
    headers: { "X-CSRF-Token": "1" },
    multipart: {
      file: {
        name: basename(path),
        mimeType: "application/dicom",
        buffer: readFileSync(path),
      },
    },
  });
  expect(upload.status(), await upload.text()).toBe(200);
  const uploaded = await upload.json();
  expect(uploaded.id, JSON.stringify(uploaded)).toBeTruthy();
  return { id: uploaded.id as number };
}

/**
 * Asserts the full happy-path render contract for an uploaded file id: the
 * header shows the stored name, the loading overlay clears, the WW/WC readout
 * goes live, the WebGL canvas is painted with multi-shade content, no error
 * alert appears, and the pixel payload was fetched via the wadouri route.
 */
async function assertViewerRenders(page: Page, fileId: number) {
  // The viewer must pull pixels via the self-contained wadouri route
  // (/files/{id}/data) — a regression to the metadata-less wadors path is
  // exactly the samplesPerPixel crash this pipeline used to have.
  let wadouriFetched = false;
  page.on("request", (req) => {
    if (req.url().includes(`/files/${fileId}/data`)) wadouriFetched = true;
  });

  // Resolve the stored name from the API — hash-dedup can return an earlier
  // row whose name differs from the uploaded basename (the ATIRA row is
  // stored under a UUID), so the header assertion must use the real name.
  const fileResp = await page.request.get(`${API_BASE}/api/files/${fileId}`);
  expect(fileResp.status(), await fileResp.text()).toBe(200);
  const fileRecord = await fileResp.json();
  expect(fileRecord.name, JSON.stringify(fileRecord)).toBeTruthy();

  await page.goto(`${BASE}/files/${fileId}`, {
    waitUntil: "domcontentloaded",
  });
  // .first(): the name can also surface in the thumbnail strip when other
  // files exist in the DB (same precedent as viewer-state.spec.ts).
  await expect(page.getByText(`File ${fileRecord.name}`).first()).toBeVisible({
    timeout: 15000,
  });

  // The viewport mounts and the loading overlay shows while the first
  // frame decodes, then clears once the image renders.
  await waitForLoadingCleared(page);

  // The WW/WC corner readout only goes non-zero once decoded pixel data
  // reached the viewport — each fixture bakes in a real window so the
  // readout is deterministic.
  await expect(page.locator(".viewportElement")).toContainText(
    /WW\/WC: [1-9]\d* \/ \d+/,
    { timeout: 20000 },
  );

  // The canvas is genuinely painted: read the WebGL drawing buffer back as
  // a PNG and count distinct sampled colors. A blank or cleared buffer is
  // uniform; each fixture's ramp + shapes produce many shades.
  const probe = await page.evaluate(async () => {
    const canvas = document.querySelector<HTMLCanvasElement>(
      ".viewportElement canvas",
    );
    if (!canvas) return { ok: false, reason: "no canvas", width: 0, height: 0 };
    const img = new Image();
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error("canvas readback decode failed"));
      img.src = canvas.toDataURL("image/png");
    });
    const probeCanvas = document.createElement("canvas");
    probeCanvas.width = img.width;
    probeCanvas.height = img.height;
    const ctx = probeCanvas.getContext("2d");
    if (!ctx) {
      return {
        ok: false,
        reason: "no 2d context",
        width: img.width,
        height: img.height,
      };
    }
    ctx.drawImage(img, 0, 0);
    const { data } = ctx.getImageData(0, 0, img.width, img.height);
    // Sample every 64th pixel — enough to prove multi-shade content without
    // iterating millions of pixels on a full-res radiograph.
    const seen = new Set<string>();
    for (let i = 0; i < data.length; i += 4 * 64) {
      seen.add(`${data[i]},${data[i + 1]},${data[i + 2]}`);
    }
    return {
      ok: seen.size > 1,
      distinct: seen.size,
      width: img.width,
      height: img.height,
    };
  });
  expect(probe, JSON.stringify(probe)).toMatchObject({ ok: true });
  expect(probe.width).toBeGreaterThan(0);
  expect(probe.height).toBeGreaterThan(0);
  expect(probe.distinct).toBeGreaterThan(1);

  // No load errors surfaced in the viewer surface (role=alert is the
  // viewportError overlay), and the pixel payload was fetched once via the
  // wadouri route.
  await expect(
    page.locator(".detail-viewport-root [role='alert']"),
  ).toHaveCount(0);
  expect(wadouriFetched).toBe(true);
}

/**
 * Best-effort capture of the loading overlay appearing (a fast decode or an
 * immediate load error may clear it before the first poll), then asserts it
 * MUST clear — a stuck "Loading image..." is the regression under test.
 */
async function waitForLoadingCleared(page: Page, appearTimeoutMs = 5000) {
  const loadingOverlay = page.locator(
    '[role="status"][aria-label="Loading image"]',
  );
  await loadingOverlay
    .waitFor({ state: "visible", timeout: appearTimeoutMs })
    .catch(() => {});
  await expect(loadingOverlay).not.toBeVisible({ timeout: 30000 });
}

test.describe("DICOM viewer render", () => {
  test("real DICOM decodes — loading overlay clears and canvas is painted", async ({
    page,
  }) => {
    await loginAsAdmin(page);
    const { id: fileId } = await uploadDicom(page);
    await assertViewerRenders(page, fileId);
  });

  test("failed pixel fetch surfaces the error overlay instead of hanging", async ({
    page,
  }) => {
    await loginAsAdmin(page);
    const { id: fileId } = await uploadDicom(page);

    // Make the wadouri pixel fetch fail while the file record stays valid:
    // the Detail page must still mount the viewer, and the viewer must clear
    // the loading overlay and surface a role=alert error instead of spinning
    // on "Loading image..." forever (the pre-fix behavior). Non-GET requests
    // (the CORS preflight) pass through to the real backend.
    let pixelFetchAttempted = false;
    await page.route(`**/files/${fileId}/data*`, async (route) => {
      if (route.request().method() === "GET") {
        pixelFetchAttempted = true;
        // ACAO header so the browser lets the XHR actually read the 404
        // status (the real failure mode) instead of rejecting it as a CORS
        // error before the loader's status check runs.
        await route.fulfill({
          status: 404,
          headers: { "Access-Control-Allow-Origin": "*" },
          contentType: "application/octet-stream",
          body: "not found",
        });
      } else {
        await route.continue();
      }
    });

    await page.goto(`${BASE}/files/${fileId}`, {
      waitUntil: "domcontentloaded",
    });

    // The loading overlay shows while the fetch is attempted, then MUST
    // clear — a stuck overlay is the regression under test.
    await waitForLoadingCleared(page, 10000);

    // The error overlay appears with the load-failure message.
    const errorAlert = page.locator(".detail-viewport-root [role='alert']");
    await expect(errorAlert).toBeVisible({ timeout: 30000 });
    await expect(errorAlert).toContainText("Failed to load DICOM image");

    // Prove the interception engaged — otherwise a URL drift would silently
    // turn this into a happy-path pass.
    expect(pixelFetchAttempted).toBe(true);
  });

  // Compressed-transfer-syntax coverage: each fixture routes through a
  // different decoder in the viewer's worker (libjpeg-turbo / CharLS), so a
  // codec regression surfaces here rather than on real modalities. These
  // always use the committed fixtures — they deliberately ignore
  // E2E_DICOM_PATH (that override targets the primary render test).
  for (const [file, label] of COMPRESSED_FIXTURES) {
    test(`compressed ${label} decodes and paints`, async ({ page }) => {
      await loginAsAdmin(page);
      const { id: fileId } = await uploadDicom(
        page,
        join(__dirname, "fixtures", file),
      );
      await assertViewerRenders(page, fileId);
    });
  }
});
