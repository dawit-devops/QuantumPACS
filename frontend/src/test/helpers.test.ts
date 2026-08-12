import { describe, it, expect, beforeEach, vi } from "vitest";
import { isAdmin, parseParams, encodeQuery } from "../helpers";
import { navigate } from "../navigator";

vi.mock("../navigator", () => ({
  navigate: vi.fn(),
}));

describe("isAdmin", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns true when admin is "true" in localStorage', () => {
    localStorage.setItem("admin", "true");
    expect(isAdmin()).toBe(true);
  });

  it("returns false when admin is not in localStorage", () => {
    expect(isAdmin()).toBe(false);
  });

  it('returns false when admin is "false" in localStorage', () => {
    localStorage.setItem("admin", "false");
    expect(isAdmin()).toBe(false);
  });
});

describe("parseParams", () => {
  it("parses URL search string into object", () => {
    const params = parseParams("?key1=value1&key2=value2");
    expect(params).toEqual({ key1: "value1", key2: "value2" });
  });

  it("returns empty object for empty search string", () => {
    const params = parseParams("");
    expect(params).toEqual({});
  });

  it("handles single parameter", () => {
    const params = parseParams("?foo=bar");
    expect(params).toEqual({ foo: "bar" });
  });
});

describe("encodeQuery", () => {
  it("encodes object to URL query string", () => {
    const query = encodeQuery({ key1: "value1", key2: "value2" });
    expect(query).toBe("key1=value1&key2=value2");
  });

  it("handles single key", () => {
    const query = encodeQuery({ foo: "bar" });
    expect(query).toBe("foo=bar");
  });

  it("encodes special characters", () => {
    const query = encodeQuery({ q: "hello world" });
    expect(query).toBe("q=hello%20world");
  });
});

describe("token helpers", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(navigate).mockClear();
  });

  it("getAccessToken always returns null (HttpOnly cookie holds it)", async () => {
    localStorage.setItem("access_token", "test-access");
    const { getAccessToken } = await import("../helpers");
    expect(getAccessToken()).toBeNull();
  });

  it("getRefreshToken always returns null (HttpOnly cookie holds it)", async () => {
    localStorage.setItem("refresh_token", "test-refresh");
    const { getRefreshToken } = await import("../helpers");
    expect(getRefreshToken()).toBeNull();
  });

  it("setTokens stores nothing (server sets the HttpOnly cookie)", async () => {
    const { setTokens } = await import("../helpers");
    setTokens("access-123", "refresh-456");
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  it("clearTokens removes both access and refresh tokens", async () => {
    localStorage.setItem("access_token", "a");
    localStorage.setItem("refresh_token", "r");
    const { clearTokens } = await import("../helpers");
    clearTokens();
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  it("tryRefreshToken posts with CSRF header and no body (cookie auth)", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: false, status: 401 });
    vi.stubGlobal("fetch", mockFetch);

    const { tryRefreshToken } = await import("../helpers");
    const result = await tryRefreshToken();

    expect(result).toBe(false);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/auth/refresh");
    expect(init.method).toBe("POST");
    expect(init.body).toBeUndefined();
    expect(init.headers.get("X-CSRF-Token")).toBe("1");
    vi.unstubAllGlobals();
  });

  it("tryRefreshToken returns true but stores nothing (cookie auth)", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          access_token: "new-access",
          refresh_token: "new-refresh",
        }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { tryRefreshToken } = await import("../helpers");
    const result = await tryRefreshToken();

    expect(result).toBe(true);
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    vi.unstubAllGlobals();
  });

  it("tryRefreshToken deduplicates concurrent calls (single-flight)", async () => {
    let resolveFetch!: (v: any) => void;
    const gate = new Promise((resolve) => {
      resolveFetch = resolve;
    });
    const mockFetch = vi.fn().mockImplementation(() => gate);
    vi.stubGlobal("fetch", mockFetch);

    const { tryRefreshToken } = await import("../helpers");
    const first = tryRefreshToken();
    const second = tryRefreshToken();
    resolveFetch({
      ok: true,
      json: () => Promise.resolve({ access_token: "t" }),
    });
    const results = await Promise.all([first, second]);

    expect(results).toEqual([true, true]);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });

  it("tryRefreshToken returns false when refresh API fails", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: false, status: 401 });
    vi.stubGlobal("fetch", mockFetch);

    const { tryRefreshToken } = await import("../helpers");
    const result = await tryRefreshToken();

    expect(result).toBe(false);
    vi.unstubAllGlobals();
  });

  it("tryRefreshToken records a 429 and wasRefreshRateLimited() reports it", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: false, status: 429 });
    vi.stubGlobal("fetch", mockFetch);

    const { tryRefreshToken, wasRefreshRateLimited } =
      await import("../helpers");
    const result = await tryRefreshToken();

    expect(result).toBe(false);
    expect(wasRefreshRateLimited()).toBe(true);
    vi.unstubAllGlobals();
  });

  it("wasRefreshRateLimited() clears after a successful refresh", async () => {
    const { tryRefreshToken, wasRefreshRateLimited } =
      await import("../helpers");
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 429 })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ access_token: "ok" }),
      });
    vi.stubGlobal("fetch", mockFetch);

    await tryRefreshToken();
    expect(wasRefreshRateLimited()).toBe(true);
    await tryRefreshToken();
    expect(wasRefreshRateLimited()).toBe(false);
    vi.unstubAllGlobals();
  });

  it("request does not navigate to /login when refresh is rate-limited (429)", async () => {
    const { request } = await import("../helpers");
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({}),
      })
      .mockResolvedValueOnce({ ok: false, status: 429 });
    vi.stubGlobal("fetch", mockFetch);

    await expect(request("test-endpoint")).rejects.toMatchObject({
      status: 401,
    });
    expect(navigate).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("request navigates to /login when refresh fails with a dead session (401)", async () => {
    const { request } = await import("../helpers");
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({}),
    });
    vi.stubGlobal("fetch", mockFetch);

    await expect(request("test-endpoint")).rejects.toMatchObject({
      status: 401,
    });
    expect(navigate).toHaveBeenCalledWith("/login");
    vi.unstubAllGlobals();
  });

  it("request sends credentials and CSRF header (cookie auth)", async () => {
    localStorage.setItem("access_token", "my-access-token");
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: "ok" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { request } = await import("../helpers");
    await request("test-endpoint");

    const { headers, credentials } = mockFetch.mock.calls[0][1];
    expect(credentials).toBe("include");
    // The access token never travels as a header (HttpOnly cookie instead).
    expect(headers.get("X-Auth-Pacs")).toBeNull();
    expect(headers.get("X-CSRF-Token")).toBe("1");
    vi.unstubAllGlobals();
  });

  it("request retries after successful token refresh on 401", async () => {
    let callCount = 0;
    const mockFetch = vi.fn().mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({}),
        });
      }
      if (callCount === 2) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              access_token: "new-access",
              refresh_token: "new-refresh",
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: "success" }),
      });
    });
    vi.stubGlobal("fetch", mockFetch);

    const { request } = await import("../helpers");
    const result = await request("test-endpoint");

    expect(result).toEqual({ data: "success" });
    // Nothing is stored client-side; the server rotates the HttpOnly cookie.
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect(mockFetch.mock.calls[2][1].credentials).toBe("include");
    expect(mockFetch.mock.calls[2][1].headers.get("X-CSRF-Token")).toBe("1");
    vi.unstubAllGlobals();
  });

  it("surfaces backend 403 as ApiError even with forged localStorage admin flag", async () => {
    // (T-M3) localStorage 'admin' is a UI convenience mirror, never an
    // authorization source: the backend decides via JWT claims. A forged
    // flag must not turn a 403 into success — the error must propagate.
    localStorage.setItem("admin", "true");
    localStorage.setItem("access_token", "attacker-token");
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: () => Promise.resolve({ error: "Missing permission: USER_ADMIN" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { request } = await import("../helpers");
    await expect(request("users")).rejects.toMatchObject({
      status: 403,
      message: expect.stringContaining("Missing permission"),
    });
    vi.unstubAllGlobals();
  });

  it("does not refresh tokens on 403 — permission is not a session problem", async () => {
    const { tryRefreshToken } = await import("../helpers");
    const refreshSpy = vi
      .spyOn({ tryRefreshToken }, "tryRefreshToken")
      .mockResolvedValue(true);
    localStorage.setItem("access_token", "t");
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: () => Promise.resolve({ error: "nope" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { request } = await import("../helpers");
    await expect(request("users")).rejects.toMatchObject({ status: 403 });
    expect(refreshSpy).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});

describe("fetchWithRetry", () => {
  it("retries GET requests on 5xx", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503 })
      .mockResolvedValueOnce({ ok: false, status: 503 })
      .mockResolvedValueOnce({ ok: true, status: 200 });
    vi.stubGlobal("fetch", mockFetch);

    const { fetchWithRetry } = await import("../helpers");
    const resp = await fetchWithRetry("http://x/api/files", {});

    expect(resp.status).toBe(200);
    expect(mockFetch).toHaveBeenCalledTimes(3);
    vi.unstubAllGlobals();
  });

  it("never retries POST/PUT/DELETE mutations", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: false, status: 503 });
    vi.stubGlobal("fetch", mockFetch);

    const { fetchWithRetry } = await import("../helpers");
    const resp = await fetchWithRetry("http://x/api/files", {
      method: "POST",
    });

    expect(resp.status).toBe(503);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });

  it("does not retry 4xx client errors", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: false, status: 422 });
    vi.stubGlobal("fetch", mockFetch);

    const { fetchWithRetry } = await import("../helpers");
    await fetchWithRetry("http://x/api/files", {});

    expect(mockFetch).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });
});
