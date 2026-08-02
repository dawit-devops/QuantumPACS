import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const { requestMock } = vi.hoisted(() => ({ requestMock: vi.fn() }));

vi.mock("../helpers", () => ({
  request: requestMock,
}));

vi.mock("../config", () => ({
  API_URL: "https://pacs.example.com/api",
  LOADING_DELAY: 300,
  PAGINATION: { limit: 10 },
}));

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = FakeWebSocket.CONNECTING;
  send = vi.fn();
  private listeners: Record<string, Function[]> = {};

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  addEventListener(type: string, fn: Function) {
    (this.listeners[type] ||= []).push(fn);
  }

  close() {
    this.readyState = FakeWebSocket.CLOSED;
    this.emit("close");
  }

  emit(type: string, ev?: any) {
    (this.listeners[type] || []).forEach((fn) => fn(ev));
  }

  simulateOpen() {
    this.readyState = FakeWebSocket.OPEN;
    this.emit("open");
  }

  simulateMessage(raw: string) {
    this.emit("message", { data: raw });
  }

  get listenerCount(): number {
    return Object.values(this.listeners).reduce((n, l) => n + l.length, 0);
  }
}

import * as ws from "../ws";

describe("ws client", () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    requestMock.mockReset();
    vi.stubGlobal("WebSocket", FakeWebSocket);
    vi.useFakeTimers();
  });

  afterEach(() => {
    ws.disconnect();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("requests a short-lived ws token and opens a wss connection", async () => {
    requestMock.mockResolvedValue({ token: "abc123" });
    ws.init();
    await vi.runAllTimersAsync();
    await Promise.resolve();

    expect(requestMock).toHaveBeenCalledWith("ws_token");
    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(FakeWebSocket.instances[0].url).toBe(
      "wss://pacs.example.com/api/ws?token=abc123",
    );
  });

  it("derives ws:// scheme from an http API_URL", async () => {
    vi.resetModules();
    vi.doMock("../config", () => ({
      API_URL: "http://pacs.local:8080/api",
      LOADING_DELAY: 300,
      PAGINATION: { limit: 10 },
    }));
    requestMock.mockResolvedValue({ token: "t1" });
    const wsHttp = await import("../ws");
    wsHttp.init();
    await vi.runAllTimersAsync();
    await Promise.resolve();

    const socket = FakeWebSocket.instances[0];
    expect(socket.url).toBe("ws://pacs.local:8080/api/ws?token=t1");
    wsHttp.disconnect();
  });

  it("delivers parsed messages to all registered listeners", async () => {
    const listenerA = vi.fn();
    const listenerB = vi.fn();
    requestMock.mockResolvedValue({ token: "abc123" });
    ws.addEventListener(listenerA);
    ws.addEventListener(listenerB);
    ws.init();
    await vi.runAllTimersAsync();
    await Promise.resolve();

    const socket = FakeWebSocket.instances[0];
    socket.simulateOpen();
    socket.simulateMessage('{"type":"update","file":1}');

    expect(listenerA).toHaveBeenCalledWith({ type: "update", file: 1 });
    expect(listenerB).toHaveBeenCalledWith({ type: "update", file: 1 });
  });

  it("ignores messages that are not valid JSON", async () => {
    const listener = vi.fn();
    requestMock.mockResolvedValue({ token: "abc123" });
    ws.addEventListener(listener);
    ws.init();
    await vi.runAllTimersAsync();
    await Promise.resolve();

    const socket = FakeWebSocket.instances[0];
    socket.simulateOpen();
    socket.simulateMessage("not-json");

    expect(listener).not.toHaveBeenCalled();
  });

  it("reconnects with capped exponential backoff after close", async () => {
    requestMock.mockResolvedValue({ token: "abc123" });
    ws.init();
    await vi.runAllTimersAsync();
    await Promise.resolve();

    FakeWebSocket.instances[0].close();
    // Jittered backoff: first delay is in [500, 1000)ms.
    await vi.advanceTimersByTimeAsync(499);
    expect(FakeWebSocket.instances).toHaveLength(1);

    await vi.advanceTimersByTimeAsync(1000);
    await vi.runAllTimersAsync();
    await Promise.resolve();
    expect(FakeWebSocket.instances.length).toBeGreaterThanOrEqual(2);
  });

  it("resets backoff after a successful open", async () => {
    requestMock.mockResolvedValue({ token: "abc123" });
    ws.init();
    await vi.runAllTimersAsync();
    await Promise.resolve();

    FakeWebSocket.instances[0].close();
    await vi.advanceTimersByTimeAsync(2000);
    await vi.runAllTimersAsync();
    await Promise.resolve();
    FakeWebSocket.instances[1].simulateOpen();

    FakeWebSocket.instances[1].close();
    await vi.advanceTimersByTimeAsync(499);
    expect(FakeWebSocket.instances).toHaveLength(2);

    await vi.advanceTimersByTimeAsync(1000);
    await vi.runAllTimersAsync();
    await Promise.resolve();
    expect(FakeWebSocket.instances.length).toBeGreaterThanOrEqual(3);
  });

  it("send() is ignored before the socket is open", async () => {
    requestMock.mockResolvedValue({ token: "abc123" });
    ws.init();
    await vi.runAllTimersAsync();
    await Promise.resolve();

    const socket = FakeWebSocket.instances[0];
    ws.send({ type: "open" });
    expect(socket.send).not.toHaveBeenCalled();

    socket.simulateOpen();
    ws.send({ type: "open" });
    expect(socket.send).toHaveBeenCalledWith('{"type":"open"}');
  });

  it("onOpen fires immediately when the socket is already open", async () => {
    const fn = vi.fn();
    requestMock.mockResolvedValue({ token: "abc123" });
    ws.init();
    await vi.runAllTimersAsync();
    await Promise.resolve();

    FakeWebSocket.instances[0].simulateOpen();
    ws.onOpen(fn);
    expect(fn).toHaveBeenCalled();
  });

  it("disconnect stops the socket and prevents reconnect", async () => {
    requestMock.mockResolvedValue({ token: "abc123" });
    ws.init();
    await vi.runAllTimersAsync();
    await Promise.resolve();

    ws.disconnect();
    await vi.advanceTimersByTimeAsync(60000);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});
