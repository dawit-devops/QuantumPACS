import React, { useEffect, useRef, useState, useCallback } from "react";
import { Select, Radio, App } from "antd";
import {
  getRenderingEngine,
  RenderingEngine,
  Enums,
  eventTarget,
  EVENTS,
  cache,
} from "@cornerstonejs/core";
import type { StackViewport } from "@cornerstonejs/core";
import { ENGINE_ID, ensureGlobalInit } from "./setup";
import { getToolGroup } from "./tools";
import { API_URL } from "../../config";
import "./StudyCompare.css";

export type CompareLayout = "2x1" | "2x2";

export interface CompareImage {
  label: string;
  imageUrl: string;
}

interface Props {
  images: CompareImage[];
  layout: CompareLayout;
  onClose: () => void;
}

const COMPARE_TOOL_GROUP_ID = "compare-tool-group";

/**
 * R-12 Multi-Study Comparison View.
 *
 * Renders 2 or 4 side-by-side viewports, each loaded with a different study.
 * Window/level changes on any viewport propagate to all others so the
 * radiologist can compare studies under identical display conditions.
 * Scroll is independent per viewport.
 */
export function StudyCompare({ images, layout, onClose }: Props) {
  const { message } = App.useApp();
  const cellCount = layout === "2x2" ? 4 : 2;
  const elementRefs = useRef<Array<HTMLDivElement | null>>([]);
  const vpIdsRef = useRef<string[]>([]);
  const disposedRef = useRef(false);
  const engineRef = useRef<ReturnType<typeof getRenderingEngine> | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Stable id per cell — created once, never changed.
  useEffect(() => {
    vpIdsRef.current = Array.from(
      { length: cellCount },
      (_, i) => `compare-${Math.random().toString(36).slice(2, 9)}-${i}`
    );
  }, [cellCount]);

  // Sync W/L from a source viewport to all others.
  const syncWl = useCallback((sourceVpId: string, voiRange: { lower: number; upper: number }) => {
    const re = engineRef.current;
    if (!re) return;
    for (const vpId of vpIdsRef.current) {
      if (vpId === sourceVpId) continue;
      const vp = re.getViewport(vpId) as StackViewport | undefined;
      if (!vp) continue;
      const current = (vp as any).voiRange;
      if (
        current &&
        Math.abs(current.lower - voiRange.lower) < 1 &&
        Math.abs(current.upper - voiRange.upper) < 1
      ) {
        continue; // already in sync
      }
      vp.setProperties({ voiRange });
      vp.render();
    }
  }, []);

  useEffect(() => {
    disposedRef.current = false;
    let cancelled = false;

    (async () => {
      try {
        await ensureGlobalInit();
        if (disposedRef.current || cancelled) return;

        let re = getRenderingEngine(ENGINE_ID);
        if (!re) re = new RenderingEngine(ENGINE_ID);
        engineRef.current = re;

        for (let i = 0; i < cellCount; i++) {
          const el = elementRefs.current[i];
          const image = images[i];
          if (!el || !image) continue;

          const vpId = vpIdsRef.current[i];
          await re.enableElement({
            viewportId: vpId,
            type: Enums.ViewportType.STACK,
            element: el,
            defaultOptions: { background: [0, 0, 0] } as any,
          });

          const tg = getToolGroup();
          if (tg) tg.addViewport(vpId, ENGINE_ID);

          const vp = re.getViewport(vpId) as StackViewport;
          if (!vp) continue;

          cache.purgeCache();
          await vp.setStack([image.imageUrl]);
          vp.render();
        }

        // Listen for W/L changes on any compare viewport → sync to others.
        const onImageRendered = (evt: any) => {
          if (disposedRef.current) return;
          const { viewportId: srcId } = evt.detail;
          const srcVp = re.getViewport(srcId) as StackViewport | undefined;
          if (!srcVp) return;
          const voiRange = (srcVp as any).voiRange;
          if (voiRange) syncWl(srcId, voiRange);
        };

        eventTarget.addEventListener(EVENTS.IMAGE_RENDERED, onImageRendered);

        return () => {
          eventTarget.removeEventListener(EVENTS.IMAGE_RENDERED, onImageRendered);
        };
      } catch (err: any) {
        if (!cancelled) setError(err?.message || "Failed to load comparison");
      }
    })();

    return () => {
      cancelled = true;
      disposedRef.current = true;
      const re = engineRef.current;
      if (re) {
        for (const vpId of vpIdsRef.current) {
          try {
            re.disableElement(vpId);
          } catch {
            /* already disabled */
          }
        }
        const tg = getToolGroup();
        if (tg) tg.removeViewports(ENGINE_ID, ...vpIdsRef.current);
      }
      cache.purgeCache();
      engineRef.current = null;
    };
  }, [cellCount, images, syncWl]);

  return (
    <div className="study-compare">
      <div className="study-compare__grid" data-layout={layout}>
        {Array.from({ length: cellCount }, (_, i) => {
          const img = images[i];
          return (
            <div key={i} className="study-compare__cell">
              <div
                className="study-compare__viewport"
                ref={(el) => {
                  elementRefs.current[i] = el;
                }}
              />
              {img && <div className="study-compare__label">{img.label}</div>}
            </div>
          );
        })}
      </div>
      {error && (
        <div className="study-compare__error" role="alert">
          {error}
        </div>
      )}
    </div>
  );
}

export default StudyCompare;
