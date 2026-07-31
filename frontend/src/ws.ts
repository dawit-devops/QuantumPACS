import { API_URL } from "./config";
import { request } from "./helpers";

const MAX_RECONNECT_DELAY = 30000;

const listeners = new Set<(data: any) => void>();
const openListeners = new Set<() => void>();
let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempts = 0;

function wsUrl(token: string): string {
  const url = new URL(API_URL);
  const scheme = url.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${url.host}/ws?token=${encodeURIComponent(token)}`;
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
      return;
    }
    listeners.forEach((fn) => fn(data));
  });
  ws.addEventListener("close", () => {
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
