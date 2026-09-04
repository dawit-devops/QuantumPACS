import React, { useCallback, useEffect, useRef } from "react";
import { UpOutlined, DownOutlined } from "@ant-design/icons";
import "./PhaseStackScroll.css";

interface PhaseStackScrollProps {
  /** Total images in the active stack (phase or single series). */
  total: number;
  /** Current zero-based index into the stack. */
  value: number;
  /** Active phase label (shown when browsing a phase stack). */
  label: string;
  onChange: (index: number) => void;
  /** Part B: stack indices (0-based) that have AI marks, for tick marks on the
   *  slice rail. When set, small violet dots indicate where marks exist. */
  tickIndices?: Set<number>;
}

// Right-hand scrollbar for the reading viewport. When a phase group is
// active the stack spans every series in the phase; the scrollbar reflects
// that full stack. Supports: up/down buttons, click-on-track jump, drag-the-
// thumb, and mouse wheel over the rail — all advance `onChange`.
export default function PhaseStackScroll({
  total,
  value,
  label,
  onChange,
  tickIndices,
}: PhaseStackScrollProps) {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const draggingRef = useRef(false);

  const clamp = useCallback(
    (i: number) => Math.max(0, Math.min(total - 1, i)),
    [total],
  );

  const step = useCallback(
    (dir: 1 | -1) => {
      if (total <= 0) return;
      onChange(clamp(value + dir));
    },
    [total, value, onChange, clamp],
  );

  const indexFromClientY = useCallback(
    (clientY: number) => {
      const track = trackRef.current;
      if (!track || total <= 1) return 0;
      const rect = track.getBoundingClientRect();
      const ratio = (clientY - rect.top) / rect.height;
      return clamp(Math.round(ratio * (total - 1)));
    },
    [total, clamp],
  );

  // Wheel over the rail pages the stack like any PACS scrollbar.
  const onWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const dir = e.deltaY > 0 ? 1 : -1;
      if (total > 0) onChange(clamp(value + dir));
    },
    [total, value, onChange, clamp],
  );

  // Drag-to-scroll with pointer capture; window listeners so a fast drag
  // doesn't lose the pointer mid-motion.
  const onThumbPointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      draggingRef.current = true;
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    },
    [],
  );
  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      if (!draggingRef.current) return;
      onChange(indexFromClientY(e.clientY));
    };
    const onUp = () => {
      draggingRef.current = false;
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [indexFromClientY, onChange]);

  const onTrackPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (e.target === e.currentTarget) {
        onChange(indexFromClientY(e.clientY));
      }
    },
    [indexFromClientY, onChange],
  );

  const thumbTop =
    total <= 1 ? 0 : (value / (total - 1)) * 100;
  const thumbHeight = Math.max(6, 100 / total);

  return (
    <div className="phase-stack-scroll" aria-label="Scroll through phase series">
      <button
        type="button"
        className="phase-stack-scroll-btn"
        onClick={() => step(-1)}
        disabled={value <= 0}
        aria-label="Previous image"
        title="Previous image"
      >
        <UpOutlined />
      </button>
      <div
        ref={trackRef}
        className="phase-stack-scroll-track"
        onPointerDown={onTrackPointerDown}
        onWheel={onWheel}
        role="slider"
        aria-valuemin={0}
        aria-valuemax={Math.max(0, total - 1)}
        aria-valuenow={value}
        aria-valuetext={`${value + 1} of ${total}`}
      >
        <div
          className="phase-stack-scroll-thumb"
          style={{ top: `${thumbTop}%`, height: `${thumbHeight}%` }}
          onPointerDown={onThumbPointerDown}
        />
        {/* Part B: AI Findings tick marks on rail — violet dots at every
            stack position that has a detection mark on another slice. */}
        {tickIndices && total > 1 && (
          <div className="phase-stack-ticks" aria-hidden="true">
            {Array.from(tickIndices).map((idx) => (
              <div
                key={idx}
                className="phase-stack-tick"
                style={{
                  top: `${(idx / (total - 1)) * 100}%`,
                }}
              />
            ))}
          </div>
        )}
      </div>
      <button
        type="button"
        className="phase-stack-scroll-btn"
        onClick={() => step(1)}
        disabled={value >= total - 1}
        aria-label="Next image"
        title="Next image"
      >
        <DownOutlined />
      </button>
      <div className="phase-stack-scroll-readout" title={label}>
        {label}
      </div>
    </div>
  );
}
