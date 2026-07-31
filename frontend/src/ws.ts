import { API_URL } from "./config";
import { request } from "./helpers";

let ws: WebSocket | null = null;
let onOpenFunc: (() => void) | null = null;
let messageFunc: ((data: any) => void) | null = null;

export function init() {
  request("ws_token")
    .then((data: any) => {
      const au = API_URL.split("//")[1];
      ws = new WebSocket(`ws://${au}/ws?token=${data.token}`);
      ws.addEventListener("open", function () {
        if (onOpenFunc) onOpenFunc();
      });
      ws.addEventListener("message", function (event: MessageEvent) {
        if (messageFunc) messageFunc(JSON.parse(event.data));
      });
      ws.addEventListener("close", function () {
        init();
      });
    })
    .catch((e: any) => {
      console.error(e);
    });
}

export function onOpen(func: () => void) {
  onOpenFunc = func;
  if (!ws) return;
  ws.addEventListener("open", function () {
    onOpenFunc!();
  });
}

export function addEventListener(func: (data: any) => void) {
  messageFunc = func;
  if (!ws) return;
  ws.addEventListener("message", function (event: MessageEvent) {
    func(JSON.parse(event.data));
  });
}

export function send(msg: any) {
  if (!ws) return;
  ws.send(JSON.stringify(msg));
}
