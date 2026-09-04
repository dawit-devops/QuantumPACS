import { getRenderingEngine, type StackViewport } from "@cornerstonejs/core";

export interface ViewportInfo {
  zoom: number;
  ww: number;
  wc: number;
}

// Viewport instances do not expose the engine directly (v5.7.2) — resolve it
// by id. The rotation/flip setters mutate camera state but never re-render
// (setRotation* fires no event, unlike setCamera), so paint explicitly to
// make the change visible.
function repaint(vp: StackViewport) {
  const re = getRenderingEngine(vp.renderingEngineId);
  if (re) void re.render();
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
  const anyVp = vp as unknown as {
    useCPURendering: boolean;
    setRotationCPU: (rotation: number) => void;
    setRotationGPU: (rotation: number) => void;
  };
  // setRotationCPU destructures _cpuFallbackEnabledElement unconditionally
  // and throws when the viewport renders on GPU — including software WebGL
  // (headless/CI), which still reports GPU mode. Pick the matching path.
  if (anyVp.useCPURendering) anyVp.setRotationCPU(rotation);
  else anyVp.setRotationGPU(rotation);
  // Neither rotation setter re-renders — mutate then paint explicitly.
  repaint(vp);
}

export function flipViewport(vp: StackViewport, vertical: boolean): void {
  // setCamera is mode-aware (routes to the CPU/GPU flip internally), unlike
  // setFlipCPU which crashes without a CPU fallback element.
  vp.setCamera({
    flipHorizontal: !vertical,
    flipVertical: vertical,
  });
  repaint(vp);
}

export function invertViewport(vp: StackViewport): void {
  vp.setProperties({ invert: !(vp as any).invert });
}

export function zoomViewport(vp: StackViewport, factor: number): void {
  vp.setZoom(vp.getZoom() * factor);
}

// The W/L the image loaded with, snapshotted once per viewport so Reset has a
// known-good target to return to regardless of what the reader dragged/baked.
const initialVoi = new WeakMap<StackViewport, { lower: number; upper: number }>();

/** Record the viewport's first observed W/L window (no-op after the first). */
export function rememberInitialVoi(vp: StackViewport): void {
  if (initialVoi.has(vp)) return;
  const voiRange = (vp as any).voiRange;
  if (voiRange && Number.isFinite(voiRange.lower) && Number.isFinite(voiRange.upper)) {
    initialVoi.set(vp, { lower: voiRange.lower, upper: voiRange.upper });
  }
}

/** Restore the viewport to its default framing: zoom 1, no rotation, no
 *  flips, invert off, and the original W/L window. (docs/viewer spec — Reset
 *  (R) returns the image to how it read on load.) */
export function resetViewport(vp: StackViewport): void {
  vp.setZoom(1);
  vp.setCamera({ flipHorizontal: false, flipVertical: false });
  const anyVp = vp as unknown as {
    useCPURendering: boolean;
    setRotationCPU: (rotation: number) => void;
    setRotationGPU: (rotation: number) => void;
  };
  if (anyVp.useCPURendering) anyVp.setRotationCPU(0);
  else anyVp.setRotationGPU(0);
  const init = initialVoi.get(vp);
  vp.setProperties({ invert: false, voiRange: init ?? (vp as any).voiRange });
  repaint(vp);
}
