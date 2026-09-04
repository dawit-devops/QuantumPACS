import type { StackViewport } from "@cornerstonejs/core";

export interface OrientationMarkers {
  top: string;
  left: string;
  bottom: string;
  right: string;
}

const DEFAULT_MARKERS: OrientationMarkers = {
  top: "A",
  left: "R",
  bottom: "P",
  right: "L",
};

function orientLPS(vector: number[]): string {
  const abs = [Math.abs(vector[0]), Math.abs(vector[1]), Math.abs(vector[2])];
  const MIN = 0.0001;
  let orientation = "";
  const label = (v: number, i: number) => {
    if (i === 0) return v < 0 ? "R" : "L";
    if (i === 1) return v < 0 ? "A" : "P";
    return v < 0 ? "F" : "H";
  };
  for (let i = 0; i < 3; i++) {
    const a = abs[0], b = abs[1], c = abs[2];
    if (a > MIN && a > b && a > c) {
      orientation += label(vector[0], 0);
      abs[0] = 0;
    } else if (b > MIN && b > a && b > c) {
      orientation += label(vector[1], 1);
      abs[1] = 0;
    } else if (c > MIN && c > a && c > b) {
      orientation += label(vector[2], 2);
      abs[2] = 0;
    } else if (a > MIN && b > MIN && a === b) {
      orientation += label(vector[0], 0) + label(vector[1], 1);
      abs[0] = 0; abs[1] = 0;
    } else if (a > MIN && c > MIN && a === c) {
      orientation += label(vector[0], 0) + label(vector[2], 2);
      abs[0] = 0; abs[2] = 0;
    } else if (b > MIN && c > MIN && b === c) {
      orientation += label(vector[1], 1) + label(vector[2], 2);
      abs[1] = 0; abs[2] = 0;
    } else { break; }
  }
  return orientation;
}

function invertLPS(orientation: string): string {
  let inv = orientation.replace("H", "f").replace("F", "h");
  inv = inv.replace("R", "l").replace("L", "r");
  inv = inv.replace("A", "p").replace("P", "a");
  return inv.toUpperCase();
}

// Read the base anatomical labels from the image's direction cosines (LPS),
// then apply the tracked camera rotation (degrees, 90° steps) and flips.
// rotationDeg parameter is tracked in component state rather than read from
// getRotation() which is unreliable across multiple Cornerstone3D rotations.
export function readOrientationMarkers(
  vp: StackViewport,
  rotationDeg = 0,
): OrientationMarkers {
  let markers = DEFAULT_MARKERS;
  try {
    const imageData = vp.getImageData();
    const dir = imageData?.direction;
    if (dir && dir.length >= 6) {
      const row = [dir[0], dir[1], dir[2]];
      const col = [dir[3], dir[4], dir[5]];
      markers = {
        right: orientLPS(row),
        bottom: orientLPS(col),
        left: invertLPS(orientLPS(row)),
        top: invertLPS(orientLPS(col)),
      };
    }
  } catch {
    markers = DEFAULT_MARKERS;
  }

  const camera = vp.getCamera();
  const steps = ((Math.round(rotationDeg / 90) % 4) + 4) % 4;

  let { top, left, bottom, right } = markers;
  for (let i = 0; i < steps; i += 1) {
    [top, right, bottom, left] = [left, top, right, bottom];
  }
  if (camera.flipHorizontal) {
    [left, right] = [right, left];
  }
  if (camera.flipVertical) {
    [top, bottom] = [bottom, top];
  }
  return { top, left, bottom, right };
}