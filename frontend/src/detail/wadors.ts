// The manager MUST come from the root package entry, not the /wadors subpath:
// vite's dep optimizer prebundles the root and the subpath as separate chunks,
// so the subpath import is a second module instance whose map the loader's
// own provider never reads (registered metadata would vanish -> the classic
// "Cannot read properties of undefined (reading 'samplesPerPixel')" crash).
import loader from "@cornerstonejs/dicom-image-loader";
import { API_URL } from "../config";
import { fetchWithRetry, handleResponse } from "../api/client";
import { wadoRsUrl } from "../api/studies";

const metaDataManager = loader.wadors.metaDataManager;

// F6.6a: WADO-RS pixel retrieval. The Cornerstone wadors loader fetches
// pixel data over multipart/related WADO-RS but resolves image-plane and
// spacing metadata from metaDataManager, keyed by the imageId's URL — a
// wadors: imageId with no registered metadata crashes in getImageFrame
// ("Cannot read properties of undefined (reading 'samplesPerPixel')").
// Registration happens here, fed by the instance /metadata dicom+json
// document; the pixel fetch itself stays with the stock loader.
//
// The feature is opt-in (localStorage qpx.viewer.wadors=1) until the
// multipart path is proven in production; the wadouri loader remains the
// default and every failure here degrades to it.

const WADORS_FLAG = "qpx.viewer.wadors";

export function wadorsRenderEnabled(): boolean {
  return localStorage.getItem(WADORS_FLAG) === "1";
}

async function fetchInstanceMetadata(
  studyUid: string,
  seriesUid: string,
  instanceUid: string,
): Promise<Record<string, unknown>[]> {
  const headers = new Headers({
    Accept: "application/dicom+json",
    "X-CSRF-Token": "1",
  });
  const tenantId = localStorage.getItem("tenant_id");
  if (tenantId) headers.set("X-Tenant-ID", tenantId);
  const resp = await fetchWithRetry(
    `${API_URL}/dicomweb/studies/${studyUid}/series/${seriesUid}/instances/${instanceUid}/metadata`,
    { headers, credentials: "include" },
  );
  const body = await handleResponse(resp);
  return Array.isArray(body) ? body : (body?.data ?? []);
}

/** Register the instance's metadata and return its wadors imageId. */
export async function prepareWadoRsImage(
  studyUid: string,
  seriesUid: string,
  instanceUid: string,
): Promise<string> {
  const [meta] = await fetchInstanceMetadata(studyUid, seriesUid, instanceUid);
  if (!meta) {
    throw new Error("WADO-RS metadata unavailable");
  }
  const imageId = wadoRsUrl(studyUid, seriesUid, instanceUid);
  metaDataManager.add(imageId, meta as never);
  return imageId;
}