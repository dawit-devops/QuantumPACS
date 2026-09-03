import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@cornerstonejs/dicom-image-loader", () => ({
  default: { wadors: { metaDataManager: { add: vi.fn() } } },
}));

vi.mock("../api/client", () => ({
  fetchWithRetry: vi.fn(),
  handleResponse: vi.fn(async (resp: any) => resp.body),
}));

import loader from "@cornerstonejs/dicom-image-loader";
import { fetchWithRetry } from "../api/client";
const metaDataManager = loader.wadors.metaDataManager as unknown as {
  add: ReturnType<typeof vi.fn>;
};
import {
  wadorsRenderEnabled,
  prepareWadoRsImage,
} from "../detail/wadors";

describe("wadors render option (F6.6a)", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("is off unless the localStorage flag is set", () => {
    expect(wadorsRenderEnabled()).toBe(false);
    localStorage.setItem("qpx.viewer.wadors", "1");
    expect(wadorsRenderEnabled()).toBe(true);
  });

  it("fetches instance metadata, registers it, and returns the wadors imageId", async () => {
    const meta = { "00080018": { vr: "UI", Value: ["1.2.3.4.5.6.7.8"] } };
    vi.mocked(fetchWithRetry).mockResolvedValue({
      ok: true,
      body: [meta],
    } as never);

    const imageId = await prepareWadoRsImage("1.2.3.4.5.6", "1.2.3.4.5.6.7", "1.2.3.4.5.6.7.8");

    expect(fetchWithRetry).toHaveBeenCalledWith(
      expect.stringContaining(
        "/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8/metadata",
      ),
      expect.objectContaining({ credentials: "include" }),
    );
    expect(metaDataManager.add).toHaveBeenCalledWith(
      expect.stringContaining("wadors:"),
      meta,
    );
    expect(imageId).toContain("wadors:");
    expect(imageId).toContain("/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8");
  });

  it("throws when the metadata payload is empty", async () => {
    vi.mocked(fetchWithRetry).mockResolvedValue({ ok: true, body: [] } as never);
    await expect(
      prepareWadoRsImage("1.2.3.4.5.6", "1.2.3.4.5.6.7", "1.2.3.4.5.6.7.8"),
    ).rejects.toThrow("WADO-RS metadata unavailable");
    expect(metaDataManager.add).not.toHaveBeenCalled();
  });
});
