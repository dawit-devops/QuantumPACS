import type { StackViewport } from "@cornerstonejs/core";

export interface ViewportInfo {
  zoom: number;
  ww: number;
  wc: number;
}

export function readViewportInfo(vp: StackViewport): ViewportInfo {
  const voiRange = (vp as any).voiRange;
  let ww = 0;
  let wc = 0;
  if (voiRange) {
    ww = voiRange.upper - voiRange.lower;
    wc = (voiRange.upper + voiRange.lower) / 2;
  }
  return { zoom: vp.getZoom(), ww, wc };
}

export function rotateViewport(vp: StackViewport): void {
  const camera = vp.getCamera();
  const rotation = ((camera.rotation || 0) + 90) % 360;
  (vp as any).setRotationCPU(rotation);
}

export function flipViewport(vp: StackViewport, vertical: boolean): void {
  (vp as any).setFlipCPU({
    flipHorizontal: !vertical,
    flipVertical: vertical,
  });
}

export function invertViewport(vp: StackViewport): void {
  vp.setProperties({ invert: !(vp as any).invert });
}

export function zoomViewport(vp: StackViewport, factor: number): void {
  vp.setZoom(vp.getZoom() * factor);
}
