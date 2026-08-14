import { useCallback, useEffect, useRef } from "react";
import type { MutableRefObject } from "react";
import { App } from "antd";
import { annotation as csAnnotation } from "@cornerstonejs/tools";
import type { StackViewport } from "@cornerstonejs/core";
import * as ws from "../../ws";
import { request } from "../../helpers";

interface UseAnnotationSyncParams {
  imageRef: MutableRefObject<string | null>;
  fileRef: MutableRefObject<any>;
  getViewport: () => StackViewport | null;
  propsRef: MutableRefObject<any>;
}

// Owns the annotation state (local mirror + WS send_state protocol) so the
// viewer component stays declarative. The class version kept the same data in
// React state only to feed a 500ms send interval; refs avoid re-renders.
export function useAnnotationSync({
  imageRef,
  fileRef,
  getViewport,
  propsRef,
}: UseAnnotationSyncParams) {
  const { message } = App.useApp();
  const stateRef = useRef<any>(null);
  const stateVerRef = useRef(0);
  const stateVerSentRef = useRef(0);

  const emitAnnotations = useCallback(() => {
    const mgr = csAnnotation.state.getAnnotationManager();
    propsRef.current.onAnnotationsChange?.(mgr.getAllAnnotations());
  }, [propsRef]);

  const saveToolState = useCallback(() => {
    const mgr = csAnnotation.state.getAnnotationManager();
    const annotations = mgr.getAllAnnotations();
    stateRef.current = annotations;
    stateVerRef.current += 1;
    propsRef.current.onAnnotationsChange?.(annotations);
  }, [propsRef]);

  const clearToolState = useCallback(() => {
    const mgr = csAnnotation.state.getAnnotationManager();
    for (const a of mgr.getAllAnnotations()) {
      csAnnotation.state.removeAnnotation(a.annotationUID);
    }
    stateRef.current = null;
    propsRef.current.onAnnotationsChange?.([]);
  }, [propsRef]);

  const restoreToolState = useCallback(
    (state: any) => {
      // Remote state arrives over WS from `send_state` (arrays from
      // getAllAnnotations) — but the backend's `open` echo replies with
      // `state: {}` when the opener sent no state. Iterating a non-array
      // throws "state is not iterable" inside the ws listener loop, so only
      // restore real annotation arrays.
      if (!Array.isArray(state)) return;
      const mgr = csAnnotation.state.getAnnotationManager();
      for (const a of mgr.getAllAnnotations()) {
        csAnnotation.state.removeAnnotation(a.annotationUID);
      }
      for (const a of state) {
        csAnnotation.state.addAnnotation(a, imageRef.current as string);
      }
    },
    [imageRef],
  );

  const focusAnnotation = useCallback(
    (annotationUID: string) => {
      const mgr = csAnnotation.state.getAnnotationManager();
      const all = mgr.getAllAnnotations();
      const annotation = all.find(
        (a: any) => a.annotationUID === annotationUID,
      );
      if (!annotation) return;

      const points = annotation.data?.handles?.points;
      if (!points || points.length === 0) return;

      const center = points
        .reduce(
          (acc: number[], p: number[]) => [
            acc[0] + p[0],
            acc[1] + p[1],
            acc[2] + p[2],
          ],
          [0, 0, 0],
        )
        .map((v: number) => v / points.length) as [number, number, number];

      const viewport = getViewport();
      if (!viewport) return;

      try {
        const camera = viewport.getCamera();
        const focal = camera.focalPoint || [0, 0, 0];
        const pos = camera.position || [0, 0, 0];
        const dx = center[0] - focal[0];
        const dy = center[1] - focal[1];
        const dz = center[2] - focal[2];
        viewport.setCamera({
          focalPoint: [focal[0] + dx, focal[1] + dy, focal[2] + dz],
          position: [pos[0] + dx, pos[1] + dy, pos[2] + dz],
        });
        viewport.render();
      } catch {}
    },
    [getViewport],
  );

  const persistToolsState = useCallback(() => {
    request(`files/${propsRef.current.file.id}`, {
      data: { tools_state: stateRef.current },
    }).catch(() => {
      message.error("Failed to persist");
    });
  }, [propsRef]);

  const sendState = useCallback(() => {
    if (stateVerRef.current > stateVerSentRef.current) {
      ws.send({
        type: "send_state",
        file: imageRef.current,
        state: stateRef.current,
        ver: stateVerRef.current,
      });
      stateVerSentRef.current = stateVerRef.current;
    }
  }, [imageRef]);

  // Remote annotations (other connected viewers) restore into this viewer.
  const onStateUpdate = useCallback(
    (data: any) => {
      if (data.type !== "send_state") return;
      if (data.file !== imageRef.current) return;
      restoreToolState(data.state);
    },
    [imageRef, restoreToolState],
  );

  useEffect(() => {
    ws.addEventListener(onStateUpdate);
    return () => ws.removeEventListener(onStateUpdate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onStateUpdate]);

  return {
    saveToolState,
    clearToolState,
    restoreToolState,
    focusAnnotation,
    emitAnnotations,
    persistToolsState,
    sendState,
    onStateUpdate,
  };
}
