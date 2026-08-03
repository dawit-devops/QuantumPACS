import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button, Collapse, Descriptions, Slider } from "antd";
import {
  ReloadOutlined,
  ColumnWidthOutlined,
  ColumnHeightOutlined,
  DragOutlined,
  RightOutlined,
  ArrowRightOutlined,
  LineOutlined,
  BorderOutlined,
  PlusCircleOutlined,
  ScissorOutlined,
  SaveOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
} from "@ant-design/icons";
import {
  getRenderingEngine,
  RenderingEngine,
  cache,
  Enums,
  eventTarget,
  EVENTS,
} from "@cornerstonejs/core";
import type { StackViewport } from "@cornerstonejs/core";
import { Enums as ToolsEnums } from "@cornerstonejs/tools";
import * as ws from "../ws";
import { API_URL } from "../config";
import { ENGINE_ID, ensureGlobalInit } from "./viewer/setup";
import {
  getToolGroup,
  activateDrag,
  activateLine,
  activateRect,
  activateElipse,
  activateAngle,
  activateArrow,
  activateEraser,
} from "./viewer/tools";
import {
  readViewportInfo,
  rotateViewport,
  flipViewport,
  invertViewport,
  zoomViewport,
} from "./viewer/camera";
import { layoutLabel, parseLayoutKey, readCurrentWL } from "./viewer/presets";
import type {
  LayoutConfig,
  ReadingPreset,
  WindowLevelConfig,
} from "./viewer/presets";
import { useReadingPresets } from "./viewer/useReadingPresets";
import type { ReadingPresetsApi } from "./viewer/useReadingPresets";
import { ReadingPresetsPanel } from "./viewer/ReadingPresetsPanel";
import { CompanionViewportGrid } from "./viewer/CompanionViewportGrid";
import { useAnnotationSync } from "./viewer/useAnnotationSync";
import ThumbnailStrip from "./ThumbnailStrip";
import { MobileToolbar } from "./MobileToolbar";
import "./CornerstoneElement.css";

const bottomLeftStyle: React.CSSProperties = {
  left: "5px",
  position: "absolute",
  color: "white",
};

const bottomRightStyle: React.CSSProperties = {
  right: "5px",
  position: "absolute",
  color: "white",
};

function InvertIcon() {
  return (
    <svg
      width="1em"
      height="1em"
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
      className=""
      viewBox="0 0 1024 1024"
    >
      <path d="M16 512c0 273.932 222.066 496 496 496s496-222.068 496-496S785.932 16 512 16 16 238.066 16 512z m496 368V144c203.41 0 368 164.622 368 368 0 203.41-164.622 368-368 368z"></path>
    </svg>
  );
}

function ActionBtn(props: any) {
  return (
    <Button
      type="primary"
      shape="circle"
      size="small"
      style={{ margin: "5px" }}
      icon={props.icon}
      onClick={props.onClick}
      aria-label={props["aria-label"] || props.tooltip || ""}
    />
  );
}

interface CEProps {
  file: any;
  files: any;
  changeFile: (v: number) => void;
  image: any;
  wadoRsImage?: string | null;
  progressive?: boolean;
  visible: boolean;
  onRequestHelp?: () => void;
  onAnnotationsChange?: (annotations: any[]) => void;
  focusAnnotationUID?: string | null;
  isMobile?: boolean;
  /** Enables the FR-R12-15 reading-presets panel + layout grid for REPORT_READ holders. */
  enableReadingPresets?: boolean;
  [key: string]: any;
}

// Functional viewer built from the viewport/tools/camera/annotation-sync
// modules. The old 1,100-line class bundled all four concerns together and
// leaked listeners/loops on unmount; every async continuation here is guarded
// by the disposed flag so teardown is complete and safe.
export default function CornerstoneElement(props: CEProps) {
  const { file, files, visible } = props;
  const imageUrl = props.wadoRsImage || props.image;

  const elementRef = useRef<HTMLDivElement | null>(null);
  const viewportIdRef = useRef(
    `stack-viewport-${Math.random().toString(36).slice(2, 9)}`,
  );
  const disposedRef = useRef(false);
  const imageRef = useRef<string | null>(imageUrl);
  const fileRef = useRef<any>(file);
  const propsRef = useRef<CEProps>(props);
  const prevFocusRef = useRef(props.focusAnnotationUID);

  const [zoom, setZoom] = useState(1);
  const [ww, setWw] = useState(0);
  const [wc, setWc] = useState(0);
  const [loading, setLoading] = useState(true);
  const [viewportError, setViewportError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showMobileToolbar, setShowMobileToolbar] = useState(false);
  const [activeTool, setActiveTool] = useState("Pan");

  // Keep latest props/file reachable from stable callbacks without re-binding
  // listeners or restarting intervals on every render.
  useEffect(() => {
    propsRef.current = props;
    fileRef.current = props.file;
  }, [props]);

  const getViewport = useCallback((): StackViewport | null => {
    const re = getRenderingEngine(ENGINE_ID);
    if (!re) return null;
    return re.getViewport(viewportIdRef.current) as StackViewport | null;
  }, []);

  // Reading presets (FR-R12-15): per-modality W/L + layout presets. Only
  // enabled for REPORT_READ holders (radiologists) to avoid idle 403 calls.
  const modality = props.file?.modality || "";
  const presets = useReadingPresets({
    modality: props.enableReadingPresets ? modality : "",
    getViewport,
  });
  const presetsRef = useRef(presets);
  useEffect(() => {
    presetsRef.current = presets;
  }, [presets]);

  const readCurrentWl = useCallback((): WindowLevelConfig => {
    const vp = getViewport();
    if (!vp) return { window_center: 0, window_width: 0 };
    return readCurrentWL(vp);
  }, [getViewport]);

  const cycleWlPreset = useCallback(() => {
    const api = presetsRef.current;
    if (!api || api.wlPresets.length === 0) return;
    // -1 (no active preset) wraps to 0, so the first press applies preset 0.
    const idx = api.wlPresets.findIndex((p) => p.id === api.activeWl?.id);
    const next = api.wlPresets[(idx + 1) % api.wlPresets.length];
    api.applyWl(next);
  }, []);

  const cycleLayout = useCallback(() => {
    const api = presetsRef.current;
    if (!api) return;
    const keys = ["1x1", "1x2", "2x2"];
    const cur = api.activeLayout
      ? layoutLabel(api.activeLayout.config as any)
      : "1x1";
    const nextKey = keys[(keys.indexOf(cur) + 1) % keys.length];
    const existing = api.layoutPresets.find(
      (p) => layoutLabel(p.config as any) === nextKey,
    );
    if (existing) {
      api.applyLayout(existing);
      return;
    }
    api.applyLayout({
      id: `std-${nextKey}`,
      preset_type: "layout",
      modality,
      name: nextKey,
      config: parseLayoutKey(nextKey),
      is_default: false,
      created_at: "",
      updated_at: "",
    } as any);
  }, [modality]);

  const layout = (presets.activeLayout?.config as LayoutConfig) || {
    rows: 1,
    cols: 1,
  };
  const cellCount = layout.rows * layout.cols;

  const updateViewportInfo = useCallback(() => {
    const vp = getViewport();
    if (!vp) return;
    const info = readViewportInfo(vp);
    setZoom(info.zoom);
    setWw(info.ww);
    setWc(info.wc);
  }, [getViewport]);

  const onImageRendered = useCallback(() => {
    updateViewportInfo();
    setLoading(false);
  }, [updateViewportInfo]);

  const onWindowResize = useCallback(() => {
    const re = getRenderingEngine(ENGINE_ID);
    if (re) re.resize();
  }, []);

  const rotate = useCallback(() => {
    const vp = getViewport();
    if (!vp) return;
    rotateViewport(vp);
  }, [getViewport]);

  const vflip = useCallback(() => {
    const vp = getViewport();
    if (!vp) return;
    flipViewport(vp, true);
  }, [getViewport]);

  const hflip = useCallback(() => {
    const vp = getViewport();
    if (!vp) return;
    flipViewport(vp, false);
  }, [getViewport]);

  const invert = useCallback(() => {
    const vp = getViewport();
    if (!vp) return;
    invertViewport(vp);
  }, [getViewport]);

  const zoomIn = useCallback(() => {
    const vp = getViewport();
    if (!vp) return;
    zoomViewport(vp, 1.2);
    updateViewportInfo();
  }, [getViewport, updateViewportInfo]);

  const zoomOut = useCallback(() => {
    const vp = getViewport();
    if (!vp) return;
    zoomViewport(vp, 1 / 1.2);
    updateViewportInfo();
  }, [getViewport, updateViewportInfo]);

  const goToPrevFile = useCallback(() => {
    const { files: list, changeFile, file: current } = propsRef.current;
    if (!list || list.length <= 1) return;
    let idx = list.findIndex((f: any) => f.id === current?.id);
    if (idx < 0) idx = 0;
    changeFile((idx - 1 + list.length) % list.length);
  }, [propsRef]);

  const goToNextFile = useCallback(() => {
    const { files: list, changeFile, file: current } = propsRef.current;
    if (!list || list.length <= 1) return;
    let idx = list.findIndex((f: any) => f.id === current?.id);
    if (idx < 0) idx = 0;
    changeFile((idx + 1) % list.length);
  }, [propsRef]);

  const toggleFullscreen = useCallback(() => {
    const el =
      document.querySelector(".detail-viewport-root") ||
      document.documentElement;
    if (!document.fullscreenElement) {
      el.requestFullscreen()
        .then(() => {
          setIsFullscreen(true);
          setTimeout(onWindowResize, 300);
        })
        .catch(() => {});
    } else {
      document
        .exitFullscreen()
        .then(() => {
          setIsFullscreen(false);
          setTimeout(onWindowResize, 300);
        })
        .catch(() => {});
    }
  }, [onWindowResize]);

  const download = useCallback(() => {
    window.open(`${API_URL}/files/${propsRef.current.file.id}/data`, "_blank");
  }, [propsRef]);

  const {
    saveToolState,
    clearToolState,
    restoreToolState,
    focusAnnotation,
    emitAnnotations,
    persistToolsState,
    sendState,
    onStateUpdate,
  } = useAnnotationSync({ imageRef, fileRef, getViewport, propsRef });

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const { visible: isVisible, onRequestHelp } = propsRef.current;
      if (!isVisible) return;

      const key = e.key;
      const target = e.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;
      if (isInput) return;

      if (key === "?") {
        e.preventDefault();
        onRequestHelp?.();
        return;
      }

      switch (key) {
        case "1":
          e.preventDefault();
          activateDrag();
          break;
        case "2":
          e.preventDefault();
          activateLine();
          break;
        case "3":
          e.preventDefault();
          activateRect();
          break;
        case "4":
          e.preventDefault();
          activateElipse();
          break;
        case "5":
          e.preventDefault();
          activateAngle();
          break;
        case "6":
          e.preventDefault();
          activateArrow();
          break;
        case "7":
        case "e":
        case "E":
          e.preventDefault();
          activateEraser();
          break;
        case "r":
        case "R":
          e.preventDefault();
          rotate();
          break;
        case "h":
        case "H":
          e.preventDefault();
          hflip();
          break;
        case "v":
        case "V":
          e.preventDefault();
          vflip();
          break;
        case "i":
        case "I":
          e.preventDefault();
          invert();
          break;
        case "p":
        case "P":
          e.preventDefault();
          cycleWlPreset();
          break;
        case "l":
        case "L":
          e.preventDefault();
          cycleLayout();
          break;
        case "s":
        case "S":
          e.preventDefault();
          persistToolsState();
          break;
        case "c":
        case "C":
          e.preventDefault();
          clearToolState();
          break;
        case "f":
        case "F":
          e.preventDefault();
          toggleFullscreen();
          break;
        case "Escape":
          if (document.fullscreenElement) {
            document.exitFullscreen();
            setIsFullscreen(false);
          }
          break;
        case "ArrowLeft":
          e.preventDefault();
          goToPrevFile();
          break;
        case "ArrowRight":
          e.preventDefault();
          goToNextFile();
          break;
        case "+":
        case "=":
          e.preventDefault();
          zoomIn();
          break;
        case "-":
          e.preventDefault();
          zoomOut();
          break;
      }
    },
    [
      rotate,
      hflip,
      vflip,
      invert,
      cycleWlPreset,
      cycleLayout,
      persistToolsState,
      clearToolState,
      toggleFullscreen,
      goToPrevFile,
      goToNextFile,
      zoomIn,
      zoomOut,
      propsRef,
    ],
  );

  // Viewport lifecycle: enable the element once, attach listeners, restore
  // persisted annotations when the engine reports a ready viewport, then keep
  // broadcasting annotation state. Every continuation bails on dispose.
  useEffect(() => {
    disposedRef.current = false;
    document.addEventListener("keydown", handleKeyDown);
    let sendInterval: ReturnType<typeof setInterval> | null = null;
    const openCb = () => ws.send({ type: "open", file: imageRef.current });

    (async () => {
      try {
        await ensureGlobalInit();
        if (disposedRef.current || !elementRef.current) return;

        let renderingEngine = getRenderingEngine(ENGINE_ID);
        if (!renderingEngine) {
          renderingEngine = new RenderingEngine(ENGINE_ID);
        }

        await renderingEngine.enableElement({
          viewportId: viewportIdRef.current,
          type: Enums.ViewportType.STACK,
          element: elementRef.current,
          defaultOptions: {
            background: [0, 0, 0],
          },
        });

        if (disposedRef.current) return;

        const tg = getToolGroup();
        if (tg) tg.addViewport(viewportIdRef.current, ENGINE_ID);

        const viewport = renderingEngine.getViewport(
          viewportIdRef.current,
        ) as StackViewport;
        await viewport.setStack([imageRef.current as string]);

        eventTarget.addEventListener(EVENTS.IMAGE_RENDERED, onImageRendered);
        eventTarget.addEventListener(EVENTS.STACK_NEW_IMAGE, onImageRendered);
        eventTarget.addEventListener(
          ToolsEnums.Events.ANNOTATION_ADDED,
          saveToolState,
        );
        eventTarget.addEventListener(
          ToolsEnums.Events.ANNOTATION_MODIFIED,
          saveToolState,
        );
        eventTarget.addEventListener(
          ToolsEnums.Events.ANNOTATION_REMOVED,
          saveToolState,
        );
        eventTarget.addEventListener(
          ToolsEnums.Events.ANNOTATION_COMPLETED,
          saveToolState,
        );
        window.addEventListener("resize", onWindowResize);

        // Wait for the engine to expose a ready viewport, but bound the
        // attempts and stop on unmount — the old loop polled forever even
        // after the element was torn down.
        let readyAttempts = 0;
        const MAX_READY_ATTEMPTS = 50; // 100ms x 50 = 5s of grace
        const checkReady = () => {
          if (disposedRef.current || readyAttempts >= MAX_READY_ATTEMPTS) {
            return;
          }
          readyAttempts += 1;
          const vp = getViewport();
          if (vp && (vp as any).voiRange) {
            restoreToolState(fileRef.current.tools_state);
            emitAnnotations();
            // AC-R12-26: auto-apply the per-modality default W/L preset once
            // the viewport is ready and before the radiologist interacts.
            presetsRef.current.applyAutoDefault();
          } else {
            setTimeout(checkReady, 100);
          }
        };
        setTimeout(checkReady, 200);

        sendInterval = setInterval(sendState, 500);
        ws.onOpen(openCb);
      } catch (e) {
        console.error("CornerstoneElement init error:", e);
        setViewportError("Failed to initialize image viewer");
        setLoading(false);
      }
    })();

    return () => {
      disposedRef.current = true;
      document.removeEventListener("keydown", handleKeyDown);
      if (sendInterval) clearInterval(sendInterval);
      window.removeEventListener("resize", onWindowResize);
      ws.removeEventListener(onStateUpdate);
      ws.removeOpenListener(openCb);
      eventTarget.removeEventListener(EVENTS.IMAGE_RENDERED, onImageRendered);
      eventTarget.removeEventListener(EVENTS.STACK_NEW_IMAGE, onImageRendered);
      eventTarget.removeEventListener(
        ToolsEnums.Events.ANNOTATION_ADDED,
        saveToolState,
      );
      eventTarget.removeEventListener(
        ToolsEnums.Events.ANNOTATION_MODIFIED,
        saveToolState,
      );
      eventTarget.removeEventListener(
        ToolsEnums.Events.ANNOTATION_REMOVED,
        saveToolState,
      );
      eventTarget.removeEventListener(
        ToolsEnums.Events.ANNOTATION_COMPLETED,
        saveToolState,
      );
      const re = getRenderingEngine(ENGINE_ID);
      if (re) {
        re.disableElement(viewportIdRef.current);
      }
      const tg = getToolGroup();
      if (tg) tg.removeViewports(ENGINE_ID, viewportIdRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Swap the stack when the parent selects a different file/series.
  useEffect(() => {
    if (imageRef.current === imageUrl) return;
    imageRef.current = imageUrl;
    // Displaying a different instance — drop the previous one's decoded
    // pixels from the shared image cache (P-M10) or RAM grows unbounded
    // while browsing a study.
    cache.purgeCache();
    const vp = getViewport();
    if (vp) {
      vp.setStack([imageUrl])
        .then(() => {
          setViewportError(null);
          setLoading(false);
          restoreToolState(fileRef.current.tools_state);
          emitAnnotations();
        })
        .catch(() => {
          setViewportError("Failed to load DICOM image");
          setLoading(false);
        });
    }
    ws.send({ type: "open", file: imageUrl });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageUrl]);

  // Measurement-panel clicks pan the camera to the annotation.
  useEffect(() => {
    const uid = props.focusAnnotationUID;
    if (uid && uid !== prevFocusRef.current) {
      focusAnnotation(uid);
    }
    prevFocusRef.current = uid;
  }, [props.focusAnnotationUID, focusAnnotation]);

  const style: React.CSSProperties = { height: "90%" };
  if (!visible) {
    style.display = "none";
  }
  let fileIndex = 0;
  if (file.id && files) {
    for (let i = 0; i < files.length; i++) {
      if (files[i].id === file.id) {
        fileIndex = i;
        break;
      }
    }
  }

  const stopAndRun = (fn: () => void) => (e: React.MouseEvent) => {
    e.stopPropagation();
    fn();
  };

  // The primary viewport (with its W/L readout and loading/error overlays).
  // Kept as one cell so multi-viewport layouts (FR-R12-15) can tile it.
  const primaryCell = (
    <div className="ce-primary-cell" style={{ position: "relative" }}>
      <div
        className="viewportElement"
        ref={elementRef}
        role="application"
        aria-label="DICOM image viewport"
        tabIndex={0}
      >
        <div style={bottomLeftStyle}>Zoom: {zoom}</div>
        <div style={bottomRightStyle}>
          WW/WC: {ww} / {wc}
        </div>
      </div>
      <div
        aria-live="polite"
        aria-atomic="true"
        style={{
          position: "absolute",
          width: 1,
          height: 1,
          overflow: "hidden",
          clip: "rect(0,0,0,0)",
        }}
      >
        {loading
          ? "Loading image"
          : `Zoom ${zoom.toFixed(1)}, Window ${ww} Level ${wc}`}
      </div>
      {viewportError ? (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(0,0,0,0.8)",
            color: "#ef4444",
            zIndex: 5,
            fontSize: 14,
            flexDirection: "column",
            gap: 12,
          }}
          role="alert"
          aria-label={viewportError}
        >
          <CloseCircleOutlined style={{ fontSize: 32 }} />
          <div>{viewportError}</div>
        </div>
      ) : (
        loading && (
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "rgba(0,0,0,0.7)",
              color: "#fff",
              zIndex: 5,
              fontSize: 14,
            }}
            role="status"
            aria-label="Loading image"
          >
            <div style={{ textAlign: "center" }}>
              <div style={{ marginBottom: 8 }}>Loading image...</div>
              <div
                style={{
                  width: 24,
                  height: 24,
                  border: "2px solid #fff",
                  borderTopColor: "transparent",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                  margin: "0 auto",
                }}
              />
            </div>
          </div>
        )
      )}
    </div>
  );

  return (
    <div
      className="detail-viewport-root"
      style={style}
      role="region"
      aria-label="DICOM image viewer"
    >
      <div style={{ padding: "10px" }} role="toolbar" aria-label="Viewer tools">
        {files && files.length > 1 && (
          <Slider
            max={files.length - 1}
            value={fileIndex}
            defaultValue={fileIndex}
            tooltip={{ formatter: (value: any) => files[value].name }}
            onChange={props.changeFile}
            aria-label={`File ${fileIndex + 1} of ${files.length}`}
          />
        )}
        <ActionBtn
          aria-label="Rotate 90 degrees clockwise"
          icon={<ReloadOutlined />}
          onClick={rotate}
        />
        <ActionBtn
          aria-label="Horizontal flip"
          icon={<ColumnWidthOutlined />}
          onClick={hflip}
        />
        <ActionBtn
          aria-label="Vertical flip"
          icon={<ColumnHeightOutlined />}
          onClick={vflip}
        />
        <Button
          type="primary"
          shape="circle"
          size="small"
          style={{ margin: "5px" }}
          onClick={invert}
          aria-label="Invert colors"
        >
          <InvertIcon />
        </Button>
        <ActionBtn
          aria-label="Pan tool"
          icon={<DragOutlined />}
          onClick={stopAndRun(activateDrag)}
        />
        <ActionBtn
          aria-label="Angle measurement"
          icon={<RightOutlined />}
          onClick={stopAndRun(activateAngle)}
        />
        <ActionBtn
          aria-label="Arrow annotation"
          icon={<ArrowRightOutlined />}
          onClick={stopAndRun(activateArrow)}
        />
        <ActionBtn
          aria-label="Length measurement"
          icon={<LineOutlined />}
          onClick={stopAndRun(activateLine)}
        />
        <ActionBtn
          aria-label="Rectangle ROI"
          icon={<BorderOutlined />}
          onClick={stopAndRun(activateRect)}
        />
        <ActionBtn
          aria-label="Ellipse ROI"
          icon={<PlusCircleOutlined />}
          onClick={stopAndRun(activateElipse)}
        />
        <ActionBtn
          aria-label="Eraser tool"
          icon={<ScissorOutlined />}
          onClick={stopAndRun(activateEraser)}
        />
        <ActionBtn
          aria-label="Save annotations"
          icon={<SaveOutlined />}
          onClick={persistToolsState}
        />
        <ActionBtn
          aria-label="Clear all annotations"
          icon={<CloseCircleOutlined />}
          onClick={clearToolState}
        />
        <ActionBtn
          aria-label="Download DICOM file"
          icon={<DownloadOutlined />}
          onClick={download}
        />
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: 8,
          padding: "4px 8px",
          background: "rgba(0,0,0,0.6)",
          zIndex: 10,
          minHeight: 44,
        }}
        role="toolbar"
        aria-label="Quick tools"
      >
        <Button
          type="default"
          shape="round"
          size="small"
          icon={<DragOutlined />}
          style={{ minWidth: 44, minHeight: 44 }}
          onClick={stopAndRun(activateDrag)}
          aria-label="Pan tool"
        />
        <Button
          type="default"
          shape="round"
          size="small"
          icon={<LineOutlined />}
          style={{ minWidth: 44, minHeight: 44 }}
          onClick={stopAndRun(activateLine)}
          aria-label="Length measurement"
        />
        <Button
          type="default"
          shape="round"
          size="small"
          icon={<BorderOutlined />}
          style={{ minWidth: 44, minHeight: 44 }}
          onClick={stopAndRun(activateRect)}
          aria-label="Rectangle ROI"
        />
        <Button
          type="default"
          shape="round"
          size="small"
          icon={<ScissorOutlined />}
          style={{ minWidth: 44, minHeight: 44 }}
          onClick={stopAndRun(activateEraser)}
          aria-label="Eraser tool"
        />
      </div>
      <ThumbnailStrip
        files={files}
        currentFileId={file.id}
        onSelect={props.changeFile}
      />
      {cellCount > 1 ? (
        <div
          className="ce-layout-grid"
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${layout.cols}, 1fr)`,
            gridTemplateRows: `repeat(${layout.rows}, 1fr)`,
            gap: 2,
            flex: 1,
            minHeight: 0,
          }}
        >
          {primaryCell}
          <CompanionViewportGrid
            layout={layout}
            imageUrl={imageUrl}
            primaryViewportId={viewportIdRef.current}
          />
        </div>
      ) : (
        primaryCell
      )}
      {props.isMobile && (
        <MobileToolbar
          activeTool={activeTool}
          onToolChange={(tool) => {
            const map: Record<string, (() => void) | undefined> = {
              Pan: activateDrag,
              Length: activateLine,
            };
            setActiveTool(tool);
            setShowMobileToolbar(true);
            map[tool]?.();
          }}
          visible={showMobileToolbar}
          onClose={() => setShowMobileToolbar(false)}
        />
      )}
      <div className="metadata-collapse">
        <Collapse
          ghost
          items={[
            {
              key: "meta",
              label: "Metadata",
              children: (
                <Descriptions size="small" column={1} bordered>
                  <Descriptions.Item label="Patient">
                    {file?.patient?.name || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Study">
                    {file?.study || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Series">
                    {file?.series || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Modality">
                    {file?.modality || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Size">
                    {file?.size ? `${(file.size / 1024).toFixed(1)} KB` : "-"}
                  </Descriptions.Item>
                </Descriptions>
              ),
            },
          ]}
        />
      </div>
      {props.enableReadingPresets && (
        <ReadingPresetsPanel
          modality={modality}
          presets={presets}
          readCurrentWl={readCurrentWl}
        />
      )}
    </div>
  );
}
