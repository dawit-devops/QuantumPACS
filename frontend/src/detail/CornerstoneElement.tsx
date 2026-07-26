import React, { Component } from 'react';
import { Button, message, Slider, Collapse, Descriptions } from 'antd';
import { ReloadOutlined, ColumnWidthOutlined, ColumnHeightOutlined, DragOutlined, RightOutlined, ArrowRightOutlined, LineOutlined, BorderOutlined, PlusCircleOutlined, ScissorOutlined, SaveOutlined, CloseCircleOutlined, DownloadOutlined } from '@ant-design/icons';
import {
  init as csCoreInit,
  RenderingEngine,
  Enums,
  eventTarget,
  EVENTS,
  getRenderingEngine,
  StackViewport,
} from '@cornerstonejs/core';
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
} from '@cornerstonejs/tools';
import { init as initDicomImageLoader } from '@cornerstonejs/dicom-image-loader';
import * as ws from '../ws';
import { request } from '../helpers';
import { API_URL } from '../config';
import './CornerstoneElement.css';

const ENGINE_ID = 'OPENPACS_ENGINE';
const TOOL_GROUP_ID = 'OPENPACS_TOOL_GROUP';

let globalInitCalled = false;

async function ensureGlobalInit() {
  if (globalInitCalled) return;
  globalInitCalled = true;

  initDicomImageLoader({
    beforeSend: (xhr: any) => {
      const token = localStorage.getItem('token') || localStorage.getItem('tempKey');
      if (token) xhr.setRequestHeader('X-Auth-Pacs', token);
    },
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
  left: '5px',
  position: 'absolute',
  color: 'white',
};

const bottomRightStyle: React.CSSProperties = {
  right: '5px',
  position: 'absolute',
  color: 'white',
};

function InvertIcon() {
  return (
    <svg width="1em" height="1em" fill="currentColor" aria-hidden="true" focusable="false" className="" viewBox="0 0 1024 1024">
      <path d="M16 512c0 273.932 222.066 496 496 496s496-222.068 496-496S785.932 16 512 16 16 238.066 16 512z m496 368V144c203.41 0 368 164.622 368 368 0 203.41-164.622 368-368 368z"></path>
    </svg>
  );
}

function ActionBtn(props: any) {
  return (
    <Button type="primary" shape="circle" size="small" style={{ margin: '5px' }}
      icon={props.icon} onClick={props.onClick}
    />
  );
}

interface CEProps {
  file: any;
  files: any;
  changeFile: (v: number) => void;
  image: any;
  visible: boolean;
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
      image: props.image,
      state: {},
      stateVer: 0,
      stateVerSent: 0,
      interval: null,
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
    this.tipFormatter = this.tipFormatter.bind(this);
    this.download = this.download.bind(this);
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

  activateArrow(_e: React.MouseEvent) {
    _e.stopPropagation();
    this.setPrimaryTool(ArrowAnnotateTool.toolName);
  }

  activateAngle(_e: React.MouseEvent) {
    _e.stopPropagation();
    this.setPrimaryTool(AngleTool.toolName);
  }

  activateLine(_e: React.MouseEvent) {
    _e.stopPropagation();
    this.setPrimaryTool(LengthTool.toolName);
  }

  activateRect(_e: React.MouseEvent) {
    _e.stopPropagation();
    this.setPrimaryTool(RectangleROITool.toolName);
  }

  activateElipse(_e: React.MouseEvent) {
    _e.stopPropagation();
    this.setPrimaryTool(EllipticalROITool.toolName);
  }

  activateDrag(_e: React.MouseEvent) {
    _e.stopPropagation();
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

  activateEraser(_e: React.MouseEvent) {
    _e.stopPropagation();
    this.setPrimaryTool(EraserTool.toolName);
  }

  onWindowResize() {
    const re = getRenderingEngine(ENGINE_ID);
    if (re) re.resize();
  }

  onImageRendered() {
    this.updateViewportInfo();
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

  saveToolState() {
    const mgr = csAnnotation.state.getAnnotationManager();
    const annotations = mgr.getAllAnnotations();
    this.setState({ state: annotations, stateVer: this.state.stateVer + 1 });
  }

  clearToolState() {
    const mgr = csAnnotation.state.getAnnotationManager();
    const existing = mgr.getAllAnnotations();
    for (const a of existing) {
      csAnnotation.state.removeAnnotation(a.annotationUID);
    }
    this.setState({ state: null as any });
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
        type: 'send_state',
        file: this.state.image,
        state: this.state.state,
        ver: this.state.stateVer,
      });
      this.setState({ stateVerSent: this.state.stateVer });
    }
  }

  onStateUpdate(data: any) {
    if (data.type !== 'send_state') return;
    if (data.file !== this.state.image) return;
    this.restoreToolState(data.state);
  }

  persistToolsState() {
    request(
      `files/${this.props.file.id}`,
      { data: { tools_state: this.state.state } },
    ).catch(
      () => {
        message.error('Failed to persist');
      }
    );
  }

  async componentDidMount() {
    this.mounted = true;

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

      const viewport = renderingEngine.getViewport(this.viewportId) as StackViewport;
      await viewport.setStack([this.state.image]);

      eventTarget.addEventListener(EVENTS.IMAGE_RENDERED, this.onImageRendered);
      eventTarget.addEventListener(EVENTS.STACK_NEW_IMAGE, this.onImageRendered);

      eventTarget.addEventListener(ToolsEnums.Events.ANNOTATION_ADDED, this.onAnnotationAdded);
      eventTarget.addEventListener(ToolsEnums.Events.ANNOTATION_MODIFIED, this.onAnnotationModified);
      eventTarget.addEventListener(ToolsEnums.Events.ANNOTATION_REMOVED, this.onAnnotationRemoved);
      eventTarget.addEventListener(ToolsEnums.Events.ANNOTATION_COMPLETED, this.onAnnotationCompleted);

      window.addEventListener('resize', this.onWindowResize);

      const that = this;
      const checkReady = () => {
        const vp = that.getViewport();
        if (vp && (vp as any).voiRange) {
          that.restoreToolState(that.props.file.tools_state);
        } else {
          setTimeout(checkReady, 100);
        }
      };
      setTimeout(checkReady, 200);

      const interval = setInterval(() => this.sendState(), 500);
      this.setState({ interval });

      ws.addEventListener(this.onStateUpdate);
      ws.onOpen(() => ws.send({ type: 'open', file: this.state.image }));
    } catch (e) {
      console.error('CornerstoneElement init error:', e);
      message.error('Failed to initialize viewer');
    }
  }

  componentDidUpdate(_prevProps: CEProps) {
    if (_prevProps.image !== this.props.image) {
      this.setState({ image: this.props.image });
      const vp = this.getViewport();
      if (vp) {
        vp.setStack([this.props.image]).then(() => {
          this.restoreToolState(this.props.file.tools_state);
        });
      }
      ws.send({ type: 'open', file: this.props.image });
    }
  }

  componentWillUnmount() {
    this.mounted = false;
    const { interval } = this.state;
    if (interval) clearInterval(interval);

    window.removeEventListener('resize', this.onWindowResize);

    const re = getRenderingEngine(ENGINE_ID);
    if (re) {
      re.disableElement(this.viewportId);
    }

    const tg = this.getToolGroup();
    if (tg) tg.removeViewports(ENGINE_ID, this.viewportId);

    eventTarget.removeEventListener(EVENTS.IMAGE_RENDERED, this.onImageRendered);
    eventTarget.removeEventListener(EVENTS.STACK_NEW_IMAGE, this.onImageRendered);
  }

  download() {
    const token = localStorage.getItem('token');
    window.open(`${API_URL}/files/${this.props.file.id}/data?token=${token}`, '_blank');
  }

  tipFormatter(value: any) {
    return `${this.props.files[value].name}`;
  }

  render() {
    const { file, files, visible } = this.props;
    const style: React.CSSProperties = { height: '90%' };
    if (!visible) {
      style.display = 'none';
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
      <div style={style}>
        <div style={{ padding: '10px' }}>
          {
            files && files.length > 1 &&
            <Slider
              max={files.length - 1}
              value={fileIndex}
              defaultValue={fileIndex}
              tooltip={{ formatter: this.tipFormatter }}
              onChange={this.props.changeFile}
            />
          }
          <ActionBtn icon={<ReloadOutlined />} onClick={this.rotate} />
          <ActionBtn icon={<ColumnWidthOutlined />} onClick={this.hflip} />
          <ActionBtn icon={<ColumnHeightOutlined />} onClick={this.vflip} />
          <Button type="primary" shape="circle" size="small"
            style={{ margin: '5px' }} onClick={this.invert} >
            <InvertIcon />
          </Button>
          <ActionBtn icon={<DragOutlined />} onClick={this.activateDrag} />
          <ActionBtn icon={<RightOutlined />} onClick={this.activateAngle} />
          <ActionBtn icon={<ArrowRightOutlined />} onClick={this.activateArrow} />
          <ActionBtn icon={<LineOutlined />} onClick={this.activateLine} />
          <ActionBtn icon={<BorderOutlined />} onClick={this.activateRect} />
          <ActionBtn icon={<PlusCircleOutlined />} onClick={this.activateElipse} />
          <ActionBtn icon={<ScissorOutlined />} onClick={this.activateEraser} />
          <ActionBtn icon={<SaveOutlined />} onClick={this.persistToolsState} />
          <ActionBtn icon={<CloseCircleOutlined />} onClick={this.clearToolState} />
          <ActionBtn icon={<DownloadOutlined />} onClick={this.download} />
        </div>
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          display: 'flex', justifyContent: 'center', gap: 8, padding: '4px 8px',
          background: 'rgba(0,0,0,0.6)', zIndex: 10,
          minHeight: 44,
        }}>
          <Button type="default" shape="round" size="small" icon={<DragOutlined />}
            style={{ minWidth: 44, minHeight: 44 }} onClick={this.activateDrag} />
          <Button type="default" shape="round" size="small" icon={<LineOutlined />}
            style={{ minWidth: 44, minHeight: 44 }} onClick={this.activateLine} />
          <Button type="default" shape="round" size="small" icon={<BorderOutlined />}
            style={{ minWidth: 44, minHeight: 44 }} onClick={this.activateRect} />
          <Button type="default" shape="round" size="small" icon={<ScissorOutlined />}
            style={{ minWidth: 44, minHeight: 44 }} onClick={this.activateEraser} />
        </div>
        <div
          className="viewportElement"
          ref={(el: HTMLDivElement | null) => {
            this.element = el;
          }}
        >
          <div style={bottomLeftStyle}>Zoom: {this.state.zoom}</div>
          <div style={bottomRightStyle}>
            WW/WC: {this.state.ww} / {this.state.wc}
          </div>
        </div>
        <div className="metadata-collapse">
          <Collapse
            ghost
            items={[
              {
                key: 'meta',
                label: 'Metadata',
                children: (
                  <Descriptions size="small" column={1} bordered>
                    <Descriptions.Item label="Patient">{file?.patient?.name || '-'}</Descriptions.Item>
                    <Descriptions.Item label="Study">{file?.study || '-'}</Descriptions.Item>
                    <Descriptions.Item label="Series">{file?.series || '-'}</Descriptions.Item>
                    <Descriptions.Item label="Modality">{file?.modality || '-'}</Descriptions.Item>
                    <Descriptions.Item label="Size">{file?.size ? `${(file.size / 1024).toFixed(1)} KB` : '-'}</Descriptions.Item>
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
