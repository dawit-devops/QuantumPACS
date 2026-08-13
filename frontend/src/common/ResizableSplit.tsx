import React, { useCallback, useRef, useState } from "react";
import "./ResizableSplit.css";

interface ResizableSplitProps {
  left: React.ReactNode;
  right: React.ReactNode;
  /** localStorage key persisting the ratio per user. */
  storageKey: string;
  /** Initial left-pane share (0..1); the persisted value wins if present. */
  initialRatio?: number;
  minLeft?: number;
  minRight?: number;
  onRatioChange?: (ratio: number) => void;
  ariaLabel?: string;
}

// Dependency-free splitter: pointer events resize a flex-basis, and the
// ratio is persisted per user so the console reopens with the same split.
// No splitter library is worth the bundle for a two-pane layout.
export default function ResizableSplit({
  left,
  right,
  storageKey,
  initialRatio = 0.55,
  minLeft = 320,
  minRight = 320,
  onRatioChange,
  ariaLabel = "Resize panels",
}: ResizableSplitProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [ratio, setRatio] = useState<number>(() => {
    const saved = Number(localStorage.getItem(storageKey));
    return Number.isFinite(saved) && saved > 0.05 && saved < 0.95
      ? saved
      : initialRatio;
  });
  const ratioRef = useRef(ratio);
  ratioRef.current = ratio;

  const persist = useCallback(
    (r: number) => {
      localStorage.setItem(storageKey, String(r));
      onRatioChange?.(r);
    },
    [onRatioChange, storageKey],
  );

  const startDrag = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      const onMove = (ev: PointerEvent) => {
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect || rect.width === 0) return;
        let next = (ev.clientX - rect.left) / rect.width;
        const leftPx = next * rect.width;
        const rightPx = rect.width - leftPx;
        // Clamp so neither pane can be dragged to nothing.
        if (leftPx < minLeft) next = minLeft / rect.width;
        else if (rightPx < minRight) next = 1 - minRight / rect.width;
        next = Math.max(0.05, Math.min(0.95, next));
        setRatio(next);
        persist(next);
      };
      const onUp = () => {
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("pointerup", onUp);
        window.removeEventListener("pointercancel", onUp);
      };
      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
      window.addEventListener("pointercancel", onUp);
    },
    [minLeft, minRight, persist],
  );

  // Keyboard resizing for the separator (role="separator" contract).
  const onKeyDown = (e: React.KeyboardEvent) => {
    const step = 0.02;
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      const next = Math.max(0.05, ratioRef.current - step);
      setRatio(next);
      persist(next);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      const next = Math.min(0.95, ratioRef.current + step);
      setRatio(next);
      persist(next);
    }
  };

  return (
    <div ref={containerRef} className="resizable-split">
      <div
        className="resizable-split-pane"
        style={{ flexBasis: `${ratio * 100}%` }}
      >
        {left}
      </div>
      <div
        className="resizable-split-handle"
        role="separator"
        aria-orientation="vertical"
        aria-label={ariaLabel}
        tabIndex={0}
        onPointerDown={startDrag}
        onKeyDown={onKeyDown}
      />
      <div className="resizable-split-pane" style={{ flex: 1 }}>
        {right}
      </div>
    </div>
  );
}
