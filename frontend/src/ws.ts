import { API_URL } from "./config";
import { request } from "./helpers";

const MAX_RECONNECT_DELAY = 30000;

// Single module-level socket shared by every subscriber (NotificationBell,
// viewer sync, ...). A per-component WebSocket would open one connection per
// mount; the Set also gives stable identity for add/removeEventListener.
const listeners = new Set<(data: any) => void>();
const openListeners = new Set<() => void>();
let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempts = 0;

function wsUrl(token: string): string {
  // Backend mounts the WS route under /api (Mount('/api', Router(routes))),
  // so the socket lives at <host><API_URL pathname>/ws — not a bare /ws.
  const url = new URL(API_URL);
  const scheme = url.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${url.host}${url.pathname}/ws?token=${encodeURIComponent(token)}`;
}

function connect(token: string): void {
  ws = new WebSocket(wsUrl(token));
  ws.addEventListener("open", () => {
    reconnectAttempts = 0;
    openListeners.forEach((fn) => fn());
  });
  ws.addEventListener("message", (event: MessageEvent) => {
    let data: any;
    try {
      data = JSON.parse(event.data);
    } catch {
      // Heartbeats/pings are not JSON — ignore, do not fan out garbage.
      return;
    }
    listeners.forEach((fn) => fn(data));
  });
  ws.addEventListener("close", () => {
    // disconnect() nulls ws BEFORE close() so a deliberate close is not
    // mistaken for a dropped connection and does not schedule a reconnect.
    if (ws === null) return;
    scheduleReconnect();
  });
}

// Capped exponential backoff with jitter so a dead server does not
// hammer the network or pile up overlapping reconnect attempts.
function scheduleReconnect(): void {
  if (reconnectTimer !== null) return;
  const base = Math.min(
    1000 * Math.pow(2, reconnectAttempts),
    MAX_RECONNECT_DELAY,
  );
  const delay = base / 2 + Math.random() * (base / 2);
  reconnectAttempts += 1;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    init();
  }, delay);
}

export function init(): void {
  // The browser API cannot set an Authorization header on a WebSocket and a
  // query-string access token would be logged by proxies, so the backend
  // issues a short-lived single-use ws_token (HttpOnly-cookie-authenticated)
  // for the handshake instead.
  request("ws_token")
    .then((data: any) => connect(data.token))
    .catch((e: any) => {
      console.error(e);
      scheduleReconnect();
    });
}

export function disconnect(): void {
  if (reconnectTimer !== null) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (ws !== null) {
    const socket = ws;
    ws = null;
    socket.close();
  }
}

export function onOpen(func: () => void): void {
  openListeners.add(func);
  // Fire immediately when the socket is already up: a late subscriber
  // (e.g. a screen mounted after login) must not wait for the next open.
  if (ws && ws.readyState === WebSocket.OPEN) {
    func();
  }
}

export function removeOpenListener(func: () => void): void {
  openListeners.delete(func);
}

export function addEventListener(func: (data: any) => void): void {
  listeners.add(func);
}

export function removeEventListener(func: (data: any) => void): void {
  listeners.delete(func);
}

export function send(msg: any): void {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify(msg));
}
