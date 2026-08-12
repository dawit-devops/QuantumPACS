import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { request } from "../api/client";

// X-Tenant-ID scoping contract (S-T1): client.ts reads the active tenant
// from localStorage per request — no React/AuthContext import — so every
// scoped screen automatically targets the right tenant after a switch.

function stubFetch(ok: boolean, body: unknown, status = ok ? 200 : 500) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

function lastFetchCall(): { url: string; options: RequestInit } {
  const fetchMock = vi.mocked(fetch);
  const call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
  return {
    url: String(call[0]),
    options: (call[1] || {}) as RequestInit,
  };
}

describe("request() tenant header", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("access_token", "test-token");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends X-Tenant-ID from localStorage tenant_id on every request", async () => {
    localStorage.setItem("tenant_id", "memorial-west");
    stubFetch(true, { data: [] });

    await request("tenants");

    const { url, options } = lastFetchCall();
    expect(url).toContain("/tenants");
    const headers = new Headers(options.headers);
    expect(headers.get("X-Tenant-ID")).toBe("memorial-west");
  });

  it("omits X-Tenant-ID when no tenant is selected", async () => {
    stubFetch(true, { data: [] });

    await request("tenants");

    const { options } = lastFetchCall();
    const headers = new Headers(options.headers);
    expect(headers.get("X-Tenant-ID")).toBeNull();
  });

  it("keeps csrf + credentials headers alongside the tenant header", async () => {
    localStorage.setItem("tenant_id", "north");
    stubFetch(true, { data: [] });

    await request("tenants");

    const { options } = lastFetchCall();
    const headers = new Headers(options.headers);
    expect(headers.get("X-Tenant-ID")).toBe("north");
    // IAM audit H-2: auth travels as an HttpOnly cookie — never in a
    // JS-readable header; the fetch must include credentials.
    expect(headers.get("X-Auth-Pacs")).toBeNull();
    expect(options.credentials).toBe("include");
    expect(headers.get("X-CSRF-Token")).toBe("1");
  });
});
