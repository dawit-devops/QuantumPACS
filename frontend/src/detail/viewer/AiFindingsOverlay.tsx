import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "antd";
import {
  CheckOutlined,
  CloseOutlined,
  QuestionCircleOutlined,
} from "@ant-design/icons";
import type { StackViewport } from "@cornerstonejs/core";
import { EVENTS } from "@cornerstonejs/core";
import type { AiMarkFinding, AiConfidence } from "./aiDetectionTypes";
import { AI_MARK_LABELS } from "./aiDetectionTypes";
import "./AiFindingsOverlay.css";

interface AiFindingsOverlayProps {
  marks: AiMarkFinding[];
  visible: boolean;
  showDismissed: boolean;
  elementRef: React.RefObject<HTMLDivElement | null>;
  getViewport: () => StackViewport | null;
  onInspect: (mark: AiMarkFinding) => void;
  onAccept: (mark: AiMarkFinding) => void;
  onDismiss: (mark: AiMarkFinding) => void;
  inspectedId?: string | null;
}

function ConfidenceTag({ confidence }: { confidence: AiConfidence }) {
  return (
    <span className={`ai-pop-conf ${confidence === "High" ? "high" : "uncertain"}`}>
      {confidence === "High" ? <CheckOutlined /> : <QuestionCircleOutlined />} {confidence}
    </span>
  );
}

/**
 * AI Findings overlay (Part B). Renders numbered ROI boxes + tags over the
 * Cornerstone viewport, positioned from the live viewport transform so marks
 * pan/zoom/rotate WITH the anatomy (B.4) instead of floating in screen space.
 *
 * Rendering strategy: the overlay holds one HTML div per mark and repositions
 * them imperatively on every render/camera event (via the same events the
 * parent listener uses). React state only changes when marks themselves
 * change (accept/dismiss/file switch), so a pan or WL drag never re-renders
 * this subtree — it just mutates transforms. This mirrors the orientation
 * letter pattern and keeps camera scrubbing at 60fps.
 *
 * Coordinate mapping: marks are stored in normalized image coordinates
 * (fraction of image width/height). At render time the viewport's imageData
 * gives the pixel dimensions and the indexToWorld transform; worldToCanvas
 * then projects to the screen pixel. zoom/pan/rotation are handled
 * transparently by the Cornerstone camera pipeline.
 */
export default function AiFindingsOverlay({
  marks,
  visible,
  showDismissed,
  elementRef,
  getViewport,
  onInspect,
  onAccept,
  onDismiss,
  inspectedId,
}: AiFindingsOverlayProps) {
  const boxRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const setBoxRef = useCallback((id: string) => (el: HTMLDivElement | null) => {
    if (el) boxRefs.current.set(id, el);
    else boxRefs.current.delete(id);
  }, []);

  // Reposition every box from the current viewport transform. Uses the vtk
  // imageData.indexToWorld (available on imageData.imageData at runtime) to
  // convert IJK pixel coords to world, then viewport.worldToCanvas to project
  // to screen. This handles zoom/pan/rotation through the Cornerstone camera
  // pipeline (B.4 — marks must move with the anatomy, not float).
  const reposition = useCallback(() => {
    const vp = getViewport();
    if (!vp) return;
    const imageData = vp.getImageData();
    if (!imageData) return;
    const [cols, rows] = imageData.dimensions;
    if (!cols || !rows) return;
    const vtkID = (imageData as any).imageData as { indexToWorld: (idx: number[]) => number[]; getDimensions: () => number[] } | undefined;
    if (!vtkID || !vtkID.indexToWorld) return;
    const { worldToCanvas } = vp;

    for (const mark of marks) {
      const el = boxRefs.current.get(mark.id);
      if (!el) continue;
      const show = mark.status !== "dismissed" || (mark.status === "dismissed" && showDismissed);
      if (!show) {
        el.style.display = "none";
        continue;
      }
      el.style.display = "block";

      const col0 = mark.x * (cols - 1);
      const row0 = mark.y * (rows - 1);
      const col1 = Math.min((mark.x + mark.w) * (cols - 1), cols - 1);
      const row1 = Math.min((mark.y + mark.h) * (rows - 1), rows - 1);

      const tlWorld = vtkID.indexToWorld([col0, row0, 0]);
      const brWorld = vtkID.indexToWorld([col1, row1, 0]);
      const tl = worldToCanvas(tlWorld as [number, number, number]);
      const br = worldToCanvas(brWorld as [number, number, number]);

      el.style.left = `${Math.min(tl[0], br[0])}px`;
      el.style.top = `${Math.min(tl[1], br[1])}px`;
      el.style.width = `${Math.max(2, Math.abs(br[0] - tl[0]))}px`;
      el.style.height = `${Math.max(2, Math.abs(br[1] - tl[1]))}px`;
      el.style.transform = "";
    }
  }, [getViewport, marks, showDismissed]);

  // Subscribe to the same element events the parent listener uses. The
  // listener functions are stable per-render; the effect re-binds only when
  // the viewport element changes. IMAGE_LOADED is global on eventTarget but
  // the parent guards by imageId; here we simply try to reposition — a no-op
  // until the image decode lands.
  useEffect(() => {
    const el = elementRef.current;
    if (!el) return;
    const onRender = () => reposition();
    const events = [EVENTS.STACK_NEW_IMAGE, EVENTS.VOI_MODIFIED, EVENTS.CAMERA_MODIFIED];
    events.forEach((evt) => el.addEventListener(evt, onRender));
    // Parent dispatches this after direct camera ops (zoom, rotate, reset,
    // flips) that fire no cornerstone events.
    el.addEventListener("ce:ai-reposition", onRender);
    window.addEventListener("resize", onRender);
    reposition();
    return () => {
      events.forEach((evt) => el.removeEventListener(evt, onRender));
      el.removeEventListener("ce:ai-reposition", onRender);
      window.removeEventListener("resize", onRender);
    };
  }, [elementRef, reposition]);

  if (!visible) return null;

  const inspected = inspectedId ? marks.find((m) => m.id === inspectedId) : null;

  return (
    <div className="ai-overlay" data-testid="ai-findings-overlay" aria-hidden="true">
      {marks.map((mark) => {
        const dismissed = mark.status === "dismissed";
        const accepted = mark.status === "accepted";
        if (dismissed && !showDismissed) return null;
        return (
          <div
            key={mark.id}
            ref={setBoxRef(mark.id)}
            className={`ai-mark${accepted ? " accepted" : ""}${dismissed ? " dismissed" : ""}`}
          >
            <div className="ai-mark-outline" />
            <button
              type="button"
              className={`ai-mark-tag${dismissed ? " dismissed" : ""}`}
              aria-label={`AI finding ${mark.number}: ${AI_MARK_LABELS[mark.kind]}`}
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => {
                e.stopPropagation();
                onInspect(mark);
              }}
            >
              {mark.number}
            </button>
          </div>
        );
      })}
      {inspected && (
        <div className="ai-pop" onClick={(e) => e.stopPropagation()}>
          <div className="ai-pop-head">
            <span className="ai-pop-kind">{AI_MARK_LABELS[inspected.kind] ?? inspected.kind}</span>
            <ConfidenceTag confidence={inspected.confidence} />
          </div>
          <div className="ai-pop-label">{inspected.label}</div>
          <div className="ai-pop-actions">
            <Button
              size="small"
              type="primary"
              icon={<CheckOutlined />}
              className="ai-pop-accept"
              onClick={() => onAccept(inspected)}
            >
              Accept
            </Button>
            <Button
              size="small"
              danger
              icon={<CloseOutlined />}
              className="ai-pop-dismiss"
              onClick={() => onDismiss(inspected)}
            >
              Dismiss
            </Button>
          </div>
          <div className="ai-pop-hint">Accepted links this finding to the report.</div>
        </div>
      )}
    </div>
  );
}