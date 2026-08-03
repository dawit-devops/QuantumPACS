import React, { useEffect, useRef } from "react";
import {
  getRenderingEngine,
  RenderingEngine,
  Enums,
  eventTarget,
  EVENTS,
} from "@cornerstonejs/core";
import type { StackViewport } from "@cornerstonejs/core";
import { ENGINE_ID, ensureGlobalInit } from "./setup";
import type { LayoutConfig } from "./presets";
import "./CompanionViewportGrid.css";

interface Props {
  layout: LayoutConfig;
  imageUrl: string;
  /** Primary viewport's id — companions mirror its W/L + camera. */
  primaryViewportId: string;
}

/**
 * Companion viewports for layout presets (FR-R12-15).
 *
 * Renders N-1 extra stack viewports that mirror the primary viewport's
 * window/level and invert state so a radiologist can tile the current series.
 * Each companion has its own element + viewport id on the shared engine; the
 * grid container uses `display: contents` so the cells slot into the parent
 * CSS grid as normal items. Teardown disables every id to avoid leaked
 * viewports in the shared rendering engine.
 */
export function CompanionViewportGrid({
  layout,
  imageUrl,
  primaryViewportId,
}: Props) {
  const cellCount = Math.max(0, layout.rows * layout.cols - 1);
  const elementRefs = useRef<Array<HTMLDivElement | null>>([]);
  const vpIdsRef = useRef<string[]>([]);
  const disposedRef = useRef(false);

  useEffect(() => {
    disposedRef.current = false;
    vpIdsRef.current = Array.from(
      { length: cellCount },
      (_, i) => `companion-${Math.random().toString(36).slice(2, 9)}-${i}`,
    );

    (async () => {
      try {
        await ensureGlobalInit();
        if (disposedRef.current) return;
        let re = getRenderingEngine(ENGINE_ID);
        if (!re) re = new RenderingEngine(ENGINE_ID);
        for (let i = 0; i < cellCount; i++) {
          const el = elementRefs.current[i];
          if (!el) continue;
          await re.enableElement({
            viewportId: vpIdsRef.current[i],
            type: Enums.ViewportType.STACK,
            element: el,
            defaultOptions: { background: [0, 0, 0] },
          });
          const vp = re.getViewport(vpIdsRef.current[i]) as StackViewport;
          if (vp) await vp.setStack([imageUrl]);
        }
      } catch (e) {
        console.error("CompanionViewportGrid init error:", e);
      }
    })();

    return () => {
      disposedRef.current = true;
      const re = getRenderingEngine(ENGINE_ID);
      if (re) {
        for (const id of vpIdsRef.current) {
          re.disableElement(id);
        }
      }
      vpIdsRef.current = [];
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cellCount]);

  // Swap the stack when the primary image changes.
  useEffect(() => {
    const re = getRenderingEngine(ENGINE_ID);
    if (!re) return;
    for (const id of vpIdsRef.current) {
      const vp = re.getViewport(id) as StackViewport | undefined;
      if (vp) vp.setStack([imageUrl]).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageUrl]);

  // Mirror the primary viewport's W/L + invert whenever it renders (covers
  // both preset applies and interactive WW/WC dragging).
  useEffect(() => {
    const onPrimaryRendered = (e: any) => {
      const detail = e.detail || {};
      if (detail.viewportId !== primaryViewportId) return;
      const re = getRenderingEngine(ENGINE_ID);
      if (!re) return;
      const primary = re.getViewport(primaryViewportId) as
        | StackViewport
        | undefined;
      if (!primary) return;
      const props: any = {
        voiRange: (primary as any).voiRange,
        invert: (primary as any).invert,
      };
      for (const id of vpIdsRef.current) {
        const vp = re.getViewport(id) as StackViewport | undefined;
        if (vp) vp.setProperties(props);
      }
    };
    eventTarget.addEventListener(EVENTS.IMAGE_RENDERED, onPrimaryRendered);
    return () =>
      eventTarget.removeEventListener(EVENTS.IMAGE_RENDERED, onPrimaryRendered);
  }, [primaryViewportId]);

  if (cellCount <= 0) return null;

  return (
    <div
      className="ce-companion-grid"
      role="group"
      aria-label="Companion viewports"
    >
      {Array.from({ length: cellCount }).map((_, i) => (
        <div
          key={i}
          ref={(el) => {
            elementRefs.current[i] = el;
          }}
          className="ce-companion-cell"
        />
      ))}
    </div>
  );
}
