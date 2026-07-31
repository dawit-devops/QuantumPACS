import React, { Component } from "react";
import { Button, message, Slider, Collapse, Descriptions } from "antd";
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
  init as csCoreInit,
  RenderingEngine,
  Enums,
  eventTarget,
  EVENTS,
  getRenderingEngine,
  StackViewport,
} from "@cornerstonejs/core";
import {
  init as csToolsInit,
  ToolGroupManager,
  addTool,
  annotation as csAnnotation,
  Enums as ToolsEnums,
  PanTool,
  ZoomTool,
  WindowLevelTool,
  LengthTool,
  RectangleROITool,
  AngleTool,
  ArrowAnnotateTool,
  EllipticalROITool,
  EraserTool,
  StackScrollTool,
} from "@cornerstonejs/tools";
import { init as initDicomImageLoader } from "@cornerstonejs/dicom-image-loader";
import * as ws from "../ws";
import { request } from "../helpers";
import { API_URL } from "../config";
import ThumbnailStrip from "./ThumbnailStrip";
import { MobileToolbar } from "./MobileToolbar";
import "./CornerstoneElement.css";

const ENGINE_ID = "OPENPACS_ENGINE";
const TOOL_GROUP_ID = "OPENPACS_TOOL_GROUP";

let globalInitCalled = false;

async function ensureGlobalInit() {
  if (globalInitCalled) return;
  globalInitCalled = true;

  initDicomImageLoader({
    beforeSend: (_xhr: any) => {},
  });

  await csCoreInit();
  await csToolsInit();

  addTool(PanTool);
  addTool(ZoomTool);
  addTool(WindowLevelTool);
  addTool(LengthTool);
  addTool(RectangleROITool);
  addTool(AngleTool);
  addTool(ArrowAnnotateTool);
  addTool(EllipticalROITool);
  addTool(EraserTool);
  addTool(StackScrollTool);

  let tg = ToolGroupManager.getToolGroup(TOOL_GROUP_ID);
  if (!tg) {
    tg = ToolGroupManager.createToolGroup(TOOL_GROUP_ID);
  }
  if (!tg) return;

  tg.addTool(PanTool.toolName);
  tg.addTool(ZoomTool.toolName);
  tg.addTool(WindowLevelTool.toolName);
  tg.addTool(LengthTool.toolName);
  tg.addTool(RectangleROITool.toolName);
  tg.addTool(AngleTool.toolName);
  tg.addTool(ArrowAnnotateTool.toolName);
  tg.addTool(EllipticalROITool.toolName);
  tg.addTool(EraserTool.toolName);
  tg.addTool(StackScrollTool.toolName);

  const setActive = (tg as any).setToolActive;
  setActive.call(tg, PanTool.toolName, { mouseButtonMask: 1 });
  setActive.call(tg, ZoomTool.toolName, { mouseButtonMask: 2 });
  setActive.call(tg, WindowLevelTool.toolName, { mouseButtonMask: 4 });
  setActive.call(tg, StackScrollTool.toolName);

  tg.setToolConfiguration(ZoomTool.toolName, {
    mouseButtonMask: 2,
    touchPinchCallback: true,
  });
  tg.setToolConfiguration(PanTool.toolName, {
    mouseButtonMask: 1,
    touchDragCallback: true,
  });
  tg.setToolConfiguration(StackScrollTool.toolName, {
    touchDragCallback: true,
  });
}

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
  [key: string]: any;
}

interface CEState {
  zoom: number;
  ww: number;
  wc: number;
  image: any;
  state: any;
  stateVer: number;
  stateVerSent: number;
  interval: any;
  loading: boolean;
  progressiveLoading: boolean;
  thumbnailUrl: string | null;
  isFullscreen: boolean;
  viewportError: string | null;
  showMobileToolbar: boolean;
  activeTool: string;
}

class CornerstoneElement extends Component<CEProps, CEState> {
  private element: HTMLDivElement | null = null;
  private viewportId: string;
  private mounted = false;

  constructor(props: CEProps) {
    super(props);
    this.viewportId = `stack-viewport-${Math.random().toString(36).slice(2, 9)}`;
    this.state = {
      zoom: 1,
      ww: 0,
      wc: 0,
      image: props.wadoRsImage || props.image,
      state: {},
      stateVer: 0,
      stateVerSent: 0,
      interval: null,
      loading: true,
      progressiveLoading: props.progressive || false,
      thumbnailUrl: null,
      isFullscreen: false,
      viewportError: null,
      showMobileToolbar: false,
      activeTool: "Pan",
    };
    this.onImageRendered = this.onImageRendered.bind(this);
    this.onWindowResize = this.onWindowResize.bind(this);
    this.onAnnotationAdded = this.onAnnotationAdded.bind(this);
    this.onAnnotationModified = this.onAnnotationModified.bind(this);
    this.onAnnotationRemoved = this.onAnnotationRemoved.bind(this);
    this.onAnnotationCompleted = this.onAnnotationCompleted.bind(this);
    this.rotate = this.rotate.bind(this);
    this.vflip = this.vflip.bind(this);
    this.hflip = this.hflip.bind(this);
    this.invert = this.invert.bind(this);
    this.onMeasurementAdded = this.onMeasurementAdded.bind(this);
    this.onMeasurementModified = this.onMeasurementModified.bind(this);
    this.onMeasurementRemoved = this.onMeasurementRemoved.bind(this);
    this.onMeasurementCompleted = this.onMeasurementCompleted.bind(this);
    this.saveToolState = this.saveToolState.bind(this);
    this.clearToolState = this.clearToolState.bind(this);
    this.restoreToolState = this.restoreToolState.bind(this);
    this.sendState = this.sendState.bind(this);
    this.onStateUpdate = this.onStateUpdate.bind(this);
    this.persistToolsState = this.persistToolsState.bind(this);
    this.emitAnnotations = this.emitAnnotations.bind(this);
    this.focusAnnotation = this.focusAnnotation.bind(this);
    this.tipFormatter = this.tipFormatter.bind(this);
    this.download = this.download.bind(this);
    this.handleKeyDown = this.handleKeyDown.bind(this);
    this.toggleFullscreen = this.toggleFullscreen.bind(this);
    this.zoomIn = this.zoomIn.bind(this);
    this.zoomOut = this.zoomOut.bind(this);
    this.goToNextFile = this.goToNextFile.bind(this);
    this.goToPrevFile = this.goToPrevFile.bind(this);
  }

  getToolGroup() {
    return ToolGroupManager.getToolGroup(TOOL_GROUP_ID);
  }

  getViewport(): StackViewport | null {
    const re = getRenderingEngine(ENGINE_ID);
    if (!re) return null;
    return re.getViewport(this.viewportId) as StackViewport | null;
  }

  private updateViewportInfo() {
    const vp = this.getViewport();
    if (!vp) return;
    const zoom = vp.getZoom();
    const voiRange = (vp as any).voiRange;
    let ww = 0;
    let wc = 0;
    if (voiRange) {
      ww = voiRange.upper - voiRange.lower;
      wc = (voiRange.upper + voiRange.lower) / 2;
    }
    this.setState({ zoom, ww, wc });
  }

  rotate() {
    const vp = this.getViewport();
    if (!vp) return;
    const camera = vp.getCamera();
    const rotation = ((camera.rotation || 0) + 90) % 360;
    (vp as any).setRotationCPU(rotation);
  }

  vflip() {
    const vp = this.getViewport();
    if (!vp) return;
    (vp as any).setFlipCPU({ flipHorizontal: false, flipVertical: true });
  }

  hflip() {
    const vp = this.getViewport();
    if (!vp) return;
    (vp as any).setFlipCPU({ flipHorizontal: true, flipVertical: false });
  }

  invert() {
    const vp = this.getViewport();
    if (!vp) return;
    vp.setProperties({ invert: !(vp as any).invert });
  }

  private setPrimaryTool(toolName: string) {
    const tg = this.getToolGroup();
    if (!tg) return;
    tg.setToolPassive(PanTool.toolName);
    (tg as any).setToolActive(toolName, { mouseButtonMask: 1 });
  }

  activateArrow(_e?: React.MouseEvent) {
    if (_e) _e.stopPropagation();
    this.setPrimaryTool(ArrowAnnotateTool.toolName);
  }

  activateAngle(_e?: React.MouseEvent) {
    if (_e) _e.stopPropagation();
    this.setPrimaryTool(AngleTool.toolName);
  }

  activateLine(_e?: React.MouseEvent) {
    if (_e) _e.stopPropagation();
    this.setPrimaryTool(LengthTool.toolName);
  }

  activateRect(_e?: React.MouseEvent) {
    if (_e) _e.stopPropagation();
    this.setPrimaryTool(RectangleROITool.toolName);
  }

  activateElipse(_e?: React.MouseEvent) {
    if (_e) _e.stopPropagation();
    this.setPrimaryTool(EllipticalROITool.toolName);
  }

  activateDrag(_e?: React.MouseEvent) {
    if (_e) _e.stopPropagation();
    const tg = this.getToolGroup();
    if (!tg) return;
    tg.setToolPassive(ArrowAnnotateTool.toolName);
    tg.setToolPassive(AngleTool.toolName);
    tg.setToolPassive(LengthTool.toolName);
    tg.setToolPassive(RectangleROITool.toolName);
    tg.setToolPassive(EllipticalROITool.toolName);
    tg.setToolPassive(EraserTool.toolName);
    (tg as any).setToolActive(PanTool.toolName, { mouseButtonMask: 1 });
  }

  activateEraser(_e?: React.MouseEvent) {
    if (_e) _e.stopPropagation();
    this.setPrimaryTool(EraserTool.toolName);
  }

  handleKeyDown(e: KeyboardEvent) {
    if (!this.props.visible) return;

    const key = e.key;
    const target = e.target as HTMLElement;
    const isInput =
      target.tagName === "INPUT" ||
      target.tagName === "TEXTAREA" ||
      target.isContentEditable;
    if (isInput) return;

    if (key === "?") {
      e.preventDefault();
      this.props.onRequestHelp?.();
      return;
    }

    switch (key) {
      case "1":
        e.preventDefault();
        this.activateDrag();
        break;
      case "2":
        e.preventDefault();
        this.activateLine();
        break;
      case "3":
        e.preventDefault();
        this.activateRect();
        break;
      case "4":
        e.preventDefault();
        this.activateElipse();
        break;
      case "5":
        e.preventDefault();
        this.activateAngle();
        break;
      case "6":
        e.preventDefault();
        this.activateArrow();
        break;
      case "7":
      case "e":
      case "E":
        e.preventDefault();
        this.activateEraser();
        break;
      case "r":
      case "R":
        e.preventDefault();
        this.rotate();
        break;
      case "h":
      case "H":
        e.preventDefault();
        this.hflip();
        break;
      case "v":
      case "V":
        e.preventDefault();
        this.vflip();
        break;
      case "i":
      case "I":
        e.preventDefault();
        this.invert();
        break;
      case "s":
      case "S":
        e.preventDefault();
        this.persistToolsState();
        break;
      case "c":
      case "C":
        e.preventDefault();
        this.clearToolState();
        break;
      case "f":
      case "F":
        e.preventDefault();
        this.toggleFullscreen();
        break;
      case "Escape":
        if (document.fullscreenElement) {
          document.exitFullscreen();
          this.setState({ isFullscreen: false });
        }
        break;
      case "ArrowLeft":
        e.preventDefault();
        this.goToPrevFile();
        break;
      case "ArrowRight":
        e.preventDefault();
        this.goToNextFile();
        break;
      case "+":
      case "=":
        e.preventDefault();
        this.zoomIn();
        break;
      case "-":
        e.preventDefault();
        this.zoomOut();
        break;
    }
  }

  toggleFullscreen() {
    const el =
      document.querySelector(".detail-viewport-root") ||
      document.documentElement;
    if (!document.fullscreenElement) {
      el.requestFullscreen()
        .then(() => {
          this.setState({ isFullscreen: true });
          setTimeout(() => this.onWindowResize(), 300);
        })
        .catch(() => {});
    } else {
      document
        .exitFullscreen()
        .then(() => {
          this.setState({ isFullscreen: false });
          setTimeout(() => this.onWindowResize(), 300);
        })
        .catch(() => {});
    }
  }

  zoomIn() {
    const vp = this.getViewport();
    if (!vp) return;
    const zoom = vp.getZoom();
    vp.setZoom(zoom * 1.2);
    this.updateViewportInfo();
  }

  zoomOut() {
    const vp = this.getViewport();
    if (!vp) return;
    const zoom = vp.getZoom();
    vp.setZoom(zoom / 1.2);
    this.updateViewportInfo();
  }

  goToPrevFile() {
    const { files, changeFile } = this.props;
    if (!files || files.length <= 1) return;
    let idx = files.findIndex((f: any) => f.id === this.props.file?.id);
    if (idx < 0) idx = 0;
    const prev = (idx - 1 + files.length) % files.length;
    changeFile(prev);
  }

  goToNextFile() {
    const { files, changeFile } = this.props;
    if (!files || files.length <= 1) return;
    let idx = files.findIndex((f: any) => f.id === this.props.file?.id);
    if (idx < 0) idx = 0;
    const next = (idx + 1) % files.length;
    changeFile(next);
  }

  onWindowResize() {
    const re = getRenderingEngine(ENGINE_ID);
    if (re) re.resize();
  }

  onImageRendered() {
    this.updateViewportInfo();
    if (this.state.loading) {
      this.setState({ loading: false });
    }
  }

  onAnnotationAdded() {
    this.saveToolState();
  }

  onAnnotationModified() {
    this.saveToolState();
  }

  onAnnotationRemoved() {
    this.saveToolState();
  }

  onAnnotationCompleted() {
    this.saveToolState();
  }

  onMeasurementAdded() {
    this.saveToolState();
  }

  onMeasurementModified() {
    this.saveToolState();
  }

  onMeasurementRemoved() {
    this.saveToolState();
  }

  onMeasurementCompleted() {
    this.saveToolState();
  }

  emitAnnotations() {
    const mgr = csAnnotation.state.getAnnotationManager();
    const annotations = mgr.getAllAnnotations();
    this.props.onAnnotationsChange?.(annotations);
  }

  saveToolState() {
    const mgr = csAnnotation.state.getAnnotationManager();
    const annotations = mgr.getAllAnnotations();
    this.setState({ state: annotations, stateVer: this.state.stateVer + 1 });
    this.props.onAnnotationsChange?.(annotations);
  }

  clearToolState() {
    const mgr = csAnnotation.state.getAnnotationManager();
    const existing = mgr.getAllAnnotations();
    for (const a of existing) {
      csAnnotation.state.removeAnnotation(a.annotationUID);
    }
    this.setState({ state: null as any });
    this.props.onAnnotationsChange?.([]);
  }

  focusAnnotation(annotationUID: string) {
    const mgr = csAnnotation.state.getAnnotationManager();
    const all = mgr.getAllAnnotations();
    const annotation = all.find((a: any) => a.annotationUID === annotationUID);
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

    const viewport = this.getViewport();
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
  }

  restoreToolState(state: any) {
    if (!state) return;
    const mgr = csAnnotation.state.getAnnotationManager();
    const existing = mgr.getAllAnnotations();
    for (const a of existing) {
      csAnnotation.state.removeAnnotation(a.annotationUID);
    }
    for (const a of state) {
      csAnnotation.state.addAnnotation(a, this.state.image);
    }
  }

  sendState() {
    if (this.state.stateVer > this.state.stateVerSent) {
      ws.send({
        type: "send_state",
        file: this.state.image,
        state: this.state.state,
        ver: this.state.stateVer,
      });
      this.setState({ stateVerSent: this.state.stateVer });
    }
  }

  onStateUpdate(data: any) {
    if (data.type !== "send_state") return;
    if (data.file !== this.state.image) return;
    this.restoreToolState(data.state);
  }

  persistToolsState() {
    request(`files/${this.props.file.id}`, {
      data: { tools_state: this.state.state },
    }).catch(() => {
      message.error("Failed to persist");
    });
  }

  async componentDidMount() {
    this.mounted = true;

    document.addEventListener("keydown", this.handleKeyDown);

    try {
      await ensureGlobalInit();

      if (!this.mounted) return;
      if (!this.element) return;

      let renderingEngine = getRenderingEngine(ENGINE_ID);
      if (!renderingEngine) {
        renderingEngine = new RenderingEngine(ENGINE_ID);
      }

      await renderingEngine.enableElement({
        viewportId: this.viewportId,
        type: Enums.ViewportType.STACK,
        element: this.element,
        defaultOptions: {
          background: [0, 0, 0],
        },
      });

      if (!this.mounted) return;

      const tg = this.getToolGroup();
      if (tg) tg.addViewport(this.viewportId, ENGINE_ID);

      const viewport = renderingEngine.getViewport(
        this.viewportId,
      ) as StackViewport;
      await viewport.setStack([this.state.image]);

      eventTarget.addEventListener(EVENTS.IMAGE_RENDERED, this.onImageRendered);
      eventTarget.addEventListener(
        EVENTS.STACK_NEW_IMAGE,
        this.onImageRendered,
      );

      eventTarget.addEventListener(
        ToolsEnums.Events.ANNOTATION_ADDED,
        this.onAnnotationAdded,
      );
      eventTarget.addEventListener(
        ToolsEnums.Events.ANNOTATION_MODIFIED,
        this.onAnnotationModified,
      );
      eventTarget.addEventListener(
        ToolsEnums.Events.ANNOTATION_REMOVED,
        this.onAnnotationRemoved,
      );
      eventTarget.addEventListener(
        ToolsEnums.Events.ANNOTATION_COMPLETED,
        this.onAnnotationCompleted,
      );

      window.addEventListener("resize", this.onWindowResize);

      const that = this;
      const checkReady = () => {
        const vp = that.getViewport();
        if (vp && (vp as any).voiRange) {
          that.restoreToolState(that.props.file.tools_state);
          that.emitAnnotations();
        } else {
          setTimeout(checkReady, 100);
        }
      };
      setTimeout(checkReady, 200);

      const interval = setInterval(() => this.sendState(), 500);
      this.setState({ interval });

      ws.addEventListener(this.onStateUpdate);
      ws.onOpen(() => ws.send({ type: "open", file: this.state.image }));
    } catch (e) {
      console.error("CornerstoneElement init error:", e);
      this.setState({
        viewportError: "Failed to initialize image viewer",
        loading: false,
      });
    }
  }

  componentDidUpdate(prevProps: CEProps) {
    const prevUrl = prevProps.wadoRsImage || prevProps.image;
    const nextUrl = this.props.wadoRsImage || this.props.image;
    if (prevUrl !== nextUrl) {
      this.setState({ image: nextUrl });
      const vp = this.getViewport();
      if (vp) {
        vp.setStack([nextUrl])
          .then(() => {
            this.setState({ viewportError: null, loading: false });
            this.restoreToolState(this.props.file.tools_state);
            this.emitAnnotations();
          })
          .catch(() => {
            this.setState({
              viewportError: "Failed to load DICOM image",
              loading: false,
            });
          });
      }
      ws.send({ type: "open", file: nextUrl });
    }

    if (
      this.props.focusAnnotationUID &&
      this.props.focusAnnotationUID !== prevProps.focusAnnotationUID
    ) {
      this.focusAnnotation(this.props.focusAnnotationUID);
    }
  }

  componentWillUnmount() {
    this.mounted = false;

    document.removeEventListener("keydown", this.handleKeyDown);

    const { interval } = this.state;
    if (interval) clearInterval(interval);

    window.removeEventListener("resize", this.onWindowResize);

    const re = getRenderingEngine(ENGINE_ID);
    if (re) {
      re.disableElement(this.viewportId);
    }

    const tg = this.getToolGroup();
    if (tg) tg.removeViewports(ENGINE_ID, this.viewportId);

    eventTarget.removeEventListener(
      EVENTS.IMAGE_RENDERED,
      this.onImageRendered,
    );
    eventTarget.removeEventListener(
      EVENTS.STACK_NEW_IMAGE,
      this.onImageRendered,
    );
  }

  download() {
    window.open(`${API_URL}/files/${this.props.file.id}/data`, "_blank");
  }

  tipFormatter(value: any) {
    return `${this.props.files[value].name}`;
  }

  render() {
    const { file, files, visible } = this.props;
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
    return (
      <div
        className="detail-viewport-root"
        style={style}
        role="region"
        aria-label="DICOM image viewer"
      >
        <div
          style={{ padding: "10px" }}
          role="toolbar"
          aria-label="Viewer tools"
        >
          {files && files.length > 1 && (
            <Slider
              max={files.length - 1}
              value={fileIndex}
              defaultValue={fileIndex}
              tooltip={{ formatter: this.tipFormatter }}
              onChange={this.props.changeFile}
              aria-label={`File ${fileIndex + 1} of ${files.length}`}
            />
          )}
          <ActionBtn
            aria-label="Rotate 90 degrees clockwise"
            icon={<ReloadOutlined />}
            onClick={this.rotate}
          />
          <ActionBtn
            aria-label="Horizontal flip"
            icon={<ColumnWidthOutlined />}
            onClick={this.hflip}
          />
          <ActionBtn
            aria-label="Vertical flip"
            icon={<ColumnHeightOutlined />}
            onClick={this.vflip}
          />
          <Button
            type="primary"
            shape="circle"
            size="small"
            style={{ margin: "5px" }}
            onClick={this.invert}
            aria-label="Invert colors"
          >
            <InvertIcon />
          </Button>
          <ActionBtn
            aria-label="Pan tool"
            icon={<DragOutlined />}
            onClick={this.activateDrag}
          />
          <ActionBtn
            aria-label="Angle measurement"
            icon={<RightOutlined />}
            onClick={this.activateAngle}
          />
          <ActionBtn
            aria-label="Arrow annotation"
            icon={<ArrowRightOutlined />}
            onClick={this.activateArrow}
          />
          <ActionBtn
            aria-label="Length measurement"
            icon={<LineOutlined />}
            onClick={this.activateLine}
          />
          <ActionBtn
            aria-label="Rectangle ROI"
            icon={<BorderOutlined />}
            onClick={this.activateRect}
          />
          <ActionBtn
            aria-label="Ellipse ROI"
            icon={<PlusCircleOutlined />}
            onClick={this.activateElipse}
          />
          <ActionBtn
            aria-label="Eraser tool"
            icon={<ScissorOutlined />}
            onClick={this.activateEraser}
          />
          <ActionBtn
            aria-label="Save annotations"
            icon={<SaveOutlined />}
            onClick={this.persistToolsState}
          />
          <ActionBtn
            aria-label="Clear all annotations"
            icon={<CloseCircleOutlined />}
            onClick={this.clearToolState}
          />
          <ActionBtn
            aria-label="Download DICOM file"
            icon={<DownloadOutlined />}
            onClick={this.download}
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
            onClick={this.activateDrag}
            aria-label="Pan tool"
          />
          <Button
            type="default"
            shape="round"
            size="small"
            icon={<LineOutlined />}
            style={{ minWidth: 44, minHeight: 44 }}
            onClick={this.activateLine}
            aria-label="Length measurement"
          />
          <Button
            type="default"
            shape="round"
            size="small"
            icon={<BorderOutlined />}
            style={{ minWidth: 44, minHeight: 44 }}
            onClick={this.activateRect}
            aria-label="Rectangle ROI"
          />
          <Button
            type="default"
            shape="round"
            size="small"
            icon={<ScissorOutlined />}
            style={{ minWidth: 44, minHeight: 44 }}
            onClick={this.activateEraser}
            aria-label="Eraser tool"
          />
        </div>
        <ThumbnailStrip
          files={files}
          currentFileId={file.id}
          onSelect={this.props.changeFile}
        />
        <div style={{ position: "relative" }}>
          <div
            className="viewportElement"
            ref={(el: HTMLDivElement | null) => {
              this.element = el;
            }}
            role="application"
            aria-label="DICOM image viewport"
            tabIndex={0}
          >
            <div style={bottomLeftStyle}>Zoom: {this.state.zoom}</div>
            <div style={bottomRightStyle}>
              WW/WC: {this.state.ww} / {this.state.wc}
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
            {this.state.loading
              ? "Loading image"
              : `Zoom ${this.state.zoom.toFixed(1)}, Window ${this.state.ww} Level ${this.state.wc}`}
          </div>
          {this.state.viewportError ? (
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
              aria-label={this.state.viewportError}
            >
              <CloseCircleOutlined style={{ fontSize: 32 }} />
              <div>{this.state.viewportError}</div>
            </div>
          ) : (
            this.state.loading && (
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
        {this.props.isMobile && (
          <MobileToolbar
            activeTool={this.state.activeTool}
            onToolChange={(tool) => {
              const map: Record<string, (() => void) | undefined> = {
                Pan: this.activateDrag,
                Length: this.activateLine,
              };
              this.setState({ activeTool: tool, showMobileToolbar: true });
              map[tool]?.();
            }}
            visible={this.state.showMobileToolbar}
            onClose={() => this.setState({ showMobileToolbar: false })}
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
      </div>
    );
  }
}

export default CornerstoneElement;
