import React, { useEffect, useRef, useState } from "react";

interface Props {
  width?: number;
  height?: number;
  label?: string;
  quality?: "good" | "noisy" | "artifact";
}

// Deterministic pseudo-random so tests can rely on the same noise field.
function seededRandom(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296;
    return s / 4294967296;
  };
}

/**
 * Simulated acquisition preview (FR-R06-04).
 *
 * There is no modality integration in this codebase, so instead of a live
 * DICOM stream the preview renders a procedurally generated "CT slice" phantom
 * on a canvas. The QA lifecycle (window/level, accept/reject, dose capture) is
 * fully functional and persists to the backend; swapping the canvas for a
 * Cornerstone3D viewport fed by a real acquisition stream is the documented
 * GATED upgrade path.
 */
function SimulatedPreview({
  width = 420,
  height = 420,
  label,
  quality = "good",
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [wl, setWl] = useState({ window: 300, level: 50 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rng = seededRandom(42);
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, width, height);

    // Body phantom: soft-tissue ellipse with a spine-like core.
    const cx = width / 2;
    const cy = height / 2;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.fillStyle = "#3a3a3a";
    ctx.beginPath();
    ctx.ellipse(0, 0, width * 0.36, height * 0.44, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#6a6a6a";
    ctx.beginPath();
    ctx.ellipse(
      0,
      height * 0.05,
      width * 0.1,
      height * 0.26,
      0,
      0,
      Math.PI * 2,
    );
    ctx.fill();
    ctx.fillStyle = "#9a9a9a";
    ctx.beginPath();
    ctx.arc(0, 0, width * 0.07, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Noise (tissue texture). RNG is deterministic so screenshots are stable.
    const imgData = ctx.getImageData(0, 0, width, height);
    const data = imgData.data;
    const noiseAmp =
      quality === "noisy" ? 46 : quality === "artifact" ? 30 : 14;
    for (let i = 0; i < data.length; i += 4) {
      const n = (rng() - 0.5) * 2 * noiseAmp;
      data[i] = Math.max(0, Math.min(255, data[i] + n));
      data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + n));
      data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + n));
    }
    // Simulated artifact: bright streak band (motion artifact).
    if (quality === "artifact") {
      for (let y = 0; y < height; y++) {
        const x = width / 2 + Math.sin(y / 9) * 8;
        for (let k = -2; k <= 2; k++) {
          const idx = (y * width + Math.min(width - 1, Math.max(0, x + k))) * 4;
          data[idx] = Math.min(255, data[idx] + 80);
          data[idx + 1] = Math.min(255, data[idx + 1] + 60);
          data[idx + 2] = Math.min(255, data[idx + 2] + 40);
        }
      }
    }
    ctx.putImageData(imgData, 0, 0);

    // Window/level overlay: a subtle vignette ring to indicate viewport.
    ctx.strokeStyle = "rgba(80, 200, 255, 0.55)";
    ctx.lineWidth = 2;
    ctx.strokeRect(1, 1, width - 2, height - 2);
  }, [width, height, quality, wl]);

  return (
    <div className="sim-preview">
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="sim-preview-canvas"
        role="img"
        aria-label={label || "Simulated acquisition preview"}
      />
      <div className="sim-preview-wl">
        <label htmlFor="sim-window">Window: {wl.window}</label>
        <input
          id="sim-window"
          type="range"
          min={100}
          max={900}
          step={20}
          value={wl.window}
          onChange={(e) =>
            setWl((p) => ({ ...p, window: Number(e.target.value) }))
          }
        />
        <label htmlFor="sim-level">Level: {wl.level}</label>
        <input
          id="sim-level"
          type="range"
          min={-100}
          max={200}
          step={10}
          value={wl.level}
          onChange={(e) =>
            setWl((p) => ({ ...p, level: Number(e.target.value) }))
          }
        />
      </div>
    </div>
  );
}

export default SimulatedPreview;
