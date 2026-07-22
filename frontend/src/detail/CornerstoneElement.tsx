import React, { Component } from 'react';
import { Button, message, Slider } from 'antd';
import { ReloadOutlined, ColumnWidthOutlined, ColumnHeightOutlined, DragOutlined, RightOutlined, ArrowRightOutlined, LineOutlined, BorderOutlined, PlusCircleOutlined, ScissorOutlined, SaveOutlined, CloseCircleOutlined, DownloadOutlined } from '@ant-design/icons';
import * as cornerstone from 'cornerstone-core';
import * as cornerstoneMath from 'cornerstone-math';
import * as cornerstoneTools from 'cornerstone-tools';
import Hammer from 'hammerjs';
import * as cornerstoneWADOImageLoader from 'cornerstone-wado-image-loader';
import dicomParser from 'dicom-parser';
import * as ws from '../ws';
import { request } from '../helpers';
import { API_URL } from '../config';
import './CornerstoneElement.css';

cornerstoneWADOImageLoader.external.cornerstone = cornerstone;
cornerstoneWADOImageLoader.external.dicomParser = dicomParser;
cornerstoneTools.external.cornerstoneMath = cornerstoneMath;
cornerstoneTools.external.cornerstone = cornerstone;
cornerstoneTools.external.Hammer = Hammer;
window.cornerstoneTools = cornerstoneTools;

cornerstoneWADOImageLoader.configure({
  beforeSend: function (xhr: any) {
    let token = localStorage.getItem('token');
    if (!token) {
      token = localStorage.getItem('tempKey');
    }
    xhr.setRequestHeader('X-Auth-Pacs', token);
  }
});

const bottomLeftStyle: React.CSSProperties = {
  left: '5px',
  position: 'absolute',
  color: 'white'
};

const bottomRightStyle: React.CSSProperties = {
  right: '5px',
  position: 'absolute',
  color: 'white'
};

function InvertIcon() {
  return (
    <svg width="1em" height="1em" fill="currentColor" aria-hidden="true" focusable="false" className="" viewBox="0 0 1024 1024">
      <path d="M16 512c0 273.932 222.066 496 496 496s496-222.068 496-496S785.932 16 512 16 16 238.066 16 512z m496 368V144c203.41 0 368 164.622 368 368 0 203.41-164.622 368-368 368z"></path>
    </svg>
  );
}

function invalidateState(state: any) {
  for (let e in state) {
    for (let t in state[e]) {
      for (let te of state[e][t].data) {
        te.invalidated = true;
        te.cachedStats = undefined;
      }
    }
  }
  return state;
}

function ActionBtn(props: any) {
  return (
    <Button type="primary" shape="circle" size='small' style={{ margin: '5px' }}
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
  state: any;
  stateVer: number;
  stateVerSent: number;
  image: any;
  viewport: any;
  interval: any;
}

class CornerstoneElement extends Component<CEProps, CEState> {
  private element: any;

  constructor(props: CEProps) {
    super(props);
    this.state = {
      viewport: cornerstone.getDefaultViewport(null, undefined),
      image: props.image,
      state: {},
      stateVer: 0,
      stateVerSent: 0,
      interval: null,
    };
    this.onImageRendered = this.onImageRendered.bind(this);
    this.onNewImage = this.onNewImage.bind(this);
    this.onWindowResize = this.onWindowResize.bind(this);
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

  rotate() {
    const viewport = cornerstone.getViewport(this.element);
    viewport.rotation += 90;
    cornerstone.setViewport(this.element, viewport);
  }

  vflip() {
    const viewport = cornerstone.getViewport(this.element);
    viewport.vflip = !viewport.vflip;
    cornerstone.setViewport(this.element, viewport);
  }

  hflip() {
    const viewport = cornerstone.getViewport(this.element);
    viewport.hflip = !viewport.hflip;
    cornerstone.setViewport(this.element, viewport);
  }

  invert() {
    const viewport = cornerstone.getViewport(this.element);
    viewport.invert = !viewport.invert;
    cornerstone.setViewport(this.element, viewport);
  }

  activateArrow(e: React.MouseEvent) {
    e.stopPropagation();
    cornerstoneTools.setToolActive('ArrowAnnotate', { mouseButtonMask: 1 });
  }

  activateAngle(e: React.MouseEvent) {
    e.stopPropagation();
    cornerstoneTools.setToolActive('Angle', { mouseButtonMask: 1 });
  }

  activateLine(e: React.MouseEvent) {
    e.stopPropagation();
    cornerstoneTools.setToolActive('Length', { mouseButtonMask: 1 });
  }

  activateRect(e: React.MouseEvent) {
    e.stopPropagation();
    cornerstoneTools.setToolActive('RectangleRoi', { mouseButtonMask: 1 });
  }

  activateElipse(e: React.MouseEvent) {
    e.stopPropagation();
    cornerstoneTools.setToolActive('EllipticalRoi', { mouseButtonMask: 1 });
  }

  activateDrag(e: React.MouseEvent) {
    e.stopPropagation();
    cornerstoneTools.setToolActive('Pan', { mouseButtonMask: 1 });
  }

  activateEraser(e: React.MouseEvent) {
    e.stopPropagation();
    cornerstoneTools.setToolActive('Eraser', { mouseButtonMask: 1 });
  }

  onWindowResize() {
    if (!this.element) return;
    cornerstone.resize(this.element);
  }

  onImageRendered() {
    const viewport = cornerstone.getViewport(this.element);
    this.setState({
      viewport
    });
  }

  onNewImage() {
    const enabledElement = cornerstone.getEnabledElement(this.element);
    this.setState({
      image: enabledElement.image.imageId
    });
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
    const s = cornerstoneTools.getElementToolStateManager(this.element).saveToolState();
    this.setState({ state: invalidateState(s), stateVer: this.state.stateVer + 1 });
  }

  clearToolState() {
    this.setState({ state: null as any });
    cornerstoneTools.getElementToolStateManager(this.element).restoreToolState({ [this.state.image]: {} });

    const viewport = cornerstone.getViewport(this.element);
    cornerstone.setViewport(this.element, viewport);
  }

  restoreToolState(state: any) {
    if (!state) return;
    state = invalidateState(state);
    cornerstoneTools.getElementToolStateManager(this.element).restoreToolState(state);

    const viewport = cornerstone.getViewport(this.element);
    if (!viewport) return;
    cornerstone.setViewport(this.element, viewport);
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

  componentDidMount() {
    const element = this.element;
    cornerstone.enable(element);
    cornerstoneTools.init({});

    const tools = [
      'PanTool', 'ZoomTool', 'WwwcTool', 'PanMultiTouchTool', 'ZoomTouchPinchTool',
      'ZoomMouseWheelTool', 'LengthTool', 'RectangleRoiTool', 'AngleTool', 'ArrowAnnotateTool',
      'EllipticalRoiTool', 'EraserTool',
    ];
    for (let t of tools) {
      cornerstoneTools.addToolForElement(element, (cornerstoneTools as any)[t]);
    }
    for (let t of tools) {
      const options: any = {};
      if (t === 'PanTool') {
        options['mouseButtonMask'] = 1;
      } else if (t === 'ZoomTool') {
        options['mouseButtonMask'] = 2;
      } else if (t === 'WwwcTool') {
        options['mouseButtonMask'] = 4;
      }
      cornerstoneTools.setToolActiveForElement(element, t.replace('Tool', ''), options);
    }

    element.addEventListener('cornerstoneimagerendered', this.onImageRendered);
    element.addEventListener('cornerstonenewimage', this.onNewImage);
    window.addEventListener('resize', this.onWindowResize);

    element.addEventListener('cornerstonetoolsmeasurementadded', this.onMeasurementAdded);
    element.addEventListener('cornerstonetoolsmeasurementmodified', this.onMeasurementModified);
    element.addEventListener('cornerstonetoolsmeasurementremoved', this.onMeasurementRemoved);
    element.addEventListener('cornerstonetoolsmeasurementcompleted', this.onMeasurementCompleted);

    const that = this;
    cornerstone.loadImage(this.state.image).then((image: any) => {
      cornerstone.displayImage(element, image);
      that.restoreToolState(that.props.file.tools_state);
    });

    const interval = setInterval(() => this.sendState(), 500);
    this.setState({ interval });

    ws.addEventListener(this.onStateUpdate);
    ws.onOpen(() => ws.send({ 'type': 'open', file: this.state.image }));
  }

  componentWillUnmount() {
    const element = this.element;
    element.removeEventListener('cornerstoneimagerendered', this.onImageRendered);
    element.removeEventListener('cornerstonenewimage', this.onNewImage);
    window.removeEventListener('resize', this.onWindowResize);
    element.removeEventListener('cornerstonetoolsmeasurementadded', this.onMeasurementAdded);
    element.removeEventListener('cornerstonetoolsmeasurementmodified', this.onMeasurementModified);
    element.removeEventListener('cornerstonetoolsmeasurementremoved', this.onMeasurementRemoved);
    element.removeEventListener('cornerstonetoolsmeasurementcompleted', this.onMeasurementCompleted);
  }

  componentWillReceiveProps(props: CEProps) {
    if (props.image !== this.state.image) {
      this.setState({ image: props.image });

      const that = this;
      cornerstone.loadImage(props.image).then((image: any) => {
        cornerstone.displayImage(that.element, image);
        that.restoreToolState(that.props.file.tools_state);
      });

      ws.send({ 'type': 'open', file: props.image });
    }
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
              tipFormatter={this.tipFormatter}
              onChange={this.props.changeFile}
            />
          }
          <ActionBtn icon={<ReloadOutlined />} onClick={this.rotate} />
          <ActionBtn icon={<ColumnWidthOutlined />} onClick={this.hflip} />
          <ActionBtn icon={<ColumnHeightOutlined />} onClick={this.vflip} />
          <Button type="primary" shape="circle" size='small'
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
        <div
          className="viewportElement"
          ref={(input: any) => {
            if (!input) return;
            this.element = input;
          }}
        >
          <canvas className="cornerstone-canvas" />
          <div style={bottomLeftStyle}>Zoom: {this.state.viewport.scale}</div>
          <div style={bottomRightStyle}>
            WW/WC: {this.state.viewport.voi.windowWidth} /{' '}
            {this.state.viewport.voi.windowCenter}
          </div>
        </div>
      </div>
    );
  }
}

export default CornerstoneElement;
