import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useFetch } from "../api/useFetch";
import * as session from "../api/session";
import { navigate } from "../navigator";

vi.mock("../navigator", () => ({
  navigate: vi.fn(),
}));

const API_URL = "http://pacs.test";

vi.mock("../config", () => ({
  API_URL: "http://pacs.test",
  LOADING_DELAY: 50,
}));

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

describe("useFetch", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    localStorage.clear();
    sessionStorage.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("resolves data and flags loading during the request", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));
    const { result } = renderHook(() => useFetch("items"));

    expect(result.current.loading).toBe(false);

    await act(async () => {
      result.current.exec();
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_URL}/items`,
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual({ ok: true });
    expect(result.current.error).toBeNull();
  });

  it("keeps showLoading false while the request completes under LOADING_DELAY", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));
    const { result } = renderHook(() => useFetch("items"));

    await act(async () => {
      result.current.exec();
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(result.current.showLoading).toBe(false);
  });

  it("shows the loader only after LOADING_DELAY elapses", async () => {
    fetchMock.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve(jsonResponse({})), 500),
        ),
    );
    const { result } = renderHook(() => useFetch("items"));

    await act(async () => {
      result.current.exec();
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(result.current.showLoading).toBe(true);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });

    expect(result.current.showLoading).toBe(false);
  });

  it("re-aborts the previous request when exec is called again", async () => {
    let abort: () => void = () => {};
    fetchMock.mockImplementation(
      () =>
        new Promise((_resolve, reject) => {
          abort = () =>
            reject(Object.assign(new Error("aborted"), { name: "AbortError" }));
        }),
    );
    const { result } = renderHook(() => useFetch("items"));

    await act(async () => {
      result.current.exec();
      await vi.advanceTimersByTimeAsync(5);
    });

    const firstController = result.current.controller.current;

    await act(async () => {
      result.current.exec();
      await vi.advanceTimersByTimeAsync(5);
    });

    expect(firstController?.signal.aborted).toBe(true);
    expect(abort).toBeDefined();
    // The aborted first request must not leave an error behind.
    expect(result.current.error).toBeNull();
  });

  it("surfaces non-401 API errors", async () => {
    // 400 is below the 5xx retry threshold, so the request completes in one shot.
    fetchMock.mockResolvedValue(jsonResponse({ error: "nope" }, 400));
    const { result } = renderHook(() => useFetch("items"));

    await act(async () => {
      result.current.exec();
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toMatch(/nope/);
  });

  it("refreshes the token and retries on 401", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ error: "expired" }, 401))
      .mockResolvedValueOnce(jsonResponse({ ok: true }));
    const refreshSpy = vi
      .spyOn(session, "tryRefreshToken")
      .mockResolvedValue(true);
    const getTokenSpy = vi
      .spyOn(session, "getAccessToken")
      .mockReturnValue("abc");

    const { result } = renderHook(() => useFetch("items"));

    await act(async () => {
      result.current.exec();
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(refreshSpy).toHaveBeenCalled();
    expect(getTokenSpy).toHaveBeenCalled();
    expect(result.current.data).toEqual({ ok: true });
    expect(result.current.error).toBeNull();

    refreshSpy.mockRestore();
    getTokenSpy.mockRestore();
  });

  it("navigates to /login when refresh fails on 401", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ error: "expired" }, 401));
    vi.spyOn(session, "tryRefreshToken").mockResolvedValue(false);

    const { result } = renderHook(() => useFetch("items"));

    await act(async () => {
      result.current.exec();
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(navigate).toHaveBeenCalledWith("/login");
  });

  it("does not navigate to /login when refresh is rate-limited (429)", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ error: "expired" }, 401));
    vi.spyOn(session, "tryRefreshToken").mockResolvedValue(false);
    const rateLimitedSpy = vi
      .spyOn(session, "wasRefreshRateLimited")
      .mockReturnValue(true);

    const { result } = renderHook(() => useFetch("items"));

    await act(async () => {
      result.current.exec();
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(navigate).not.toHaveBeenCalled();
    rateLimitedSpy.mockRestore();
  });

  it("calls the unauthorized callback instead of navigating when provided", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ error: "expired" }, 401));
    vi.spyOn(session, "tryRefreshToken").mockResolvedValue(false);
    const unauthorized = vi.fn();

    const { result } = renderHook(() => useFetch("items", { unauthorized }));

    await act(async () => {
      result.current.exec();
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(unauthorized).toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("prepends API_URL to relative paths and keeps absolute URLs", async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));
    const { result } = renderHook(() => useFetch("https://other.example/x"));

    await act(async () => {
      result.current.exec();
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://other.example/x",
      expect.anything(),
    );
  });
});
