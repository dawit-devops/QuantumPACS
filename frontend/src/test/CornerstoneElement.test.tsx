import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CornerstoneElement from '../detail/CornerstoneElement';

vi.mock('@cornerstonejs/core', () => ({
  init: vi.fn(),
  RenderingEngine: vi.fn(() => ({
    enableElement: vi.fn(),
    getViewport: vi.fn(),
    resize: vi.fn(),
    disableElement: vi.fn(),
  })),
  Enums: { ViewportType: { STACK: 'stack' } },
  eventTarget: { addEventListener: vi.fn(), removeEventListener: vi.fn() },
  EVENTS: { IMAGE_RENDERED: 'imageRendered', STACK_NEW_IMAGE: 'stackNewImage' },
  getRenderingEngine: vi.fn(),
  StackViewport: vi.fn(),
}));

vi.mock('@cornerstonejs/tools', () => ({
  init: vi.fn(),
  ToolGroupManager: {
    getToolGroup: vi.fn(),
    createToolGroup: vi.fn(() => ({
      addTool: vi.fn(),
      addViewport: vi.fn(),
      removeViewports: vi.fn(),
      setToolPassive: vi.fn(),
      setToolActive: vi.fn(),
    })),
  },
  addTool: vi.fn(),
  annotation: { state: { getAnnotationManager: vi.fn(() => ({ getAllAnnotations: vi.fn(() => []), removeAnnotation: vi.fn(), addAnnotation: vi.fn() })) } },
  Enums: { Events: { ANNOTATION_ADDED: 'added', ANNOTATION_MODIFIED: 'modified', ANNOTATION_REMOVED: 'removed', ANNOTATION_COMPLETED: 'completed' } },
  PanTool: { toolName: 'Pan' },
  ZoomTool: { toolName: 'Zoom' },
  WindowLevelTool: { toolName: 'WindowLevel' },
  LengthTool: { toolName: 'Length' },
  RectangleROITool: { toolName: 'RectangleROI' },
  AngleTool: { toolName: 'Angle' },
  ArrowAnnotateTool: { toolName: 'ArrowAnnotate' },
  EllipticalROITool: { toolName: 'EllipticalROI' },
  EraserTool: { toolName: 'Eraser' },
  StackScrollTool: { toolName: 'StackScroll' },
}));

vi.mock('@cornerstonejs/dicom-image-loader', () => ({
  init: vi.fn(),
}));

vi.mock('../ws', () => ({
  default: { addEventListener: vi.fn(), onOpen: vi.fn(), send: vi.fn() },
}));

vi.mock('../helpers', () => ({
  request: vi.fn(),
}));

describe('CornerstoneElement', () => {
  const defaultProps = {
    file: { id: '1', name: 'test.dcm', tools_state: null },
    files: [{ id: '1', name: 'test.dcm' }],
    changeFile: vi.fn(),
    image: 'wsi://test',
    visible: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders viewport element', () => {
    const { container } = render(<CornerstoneElement {...defaultProps} />);
    const viewportEl = container.querySelector('.viewportElement');
    expect(viewportEl).toBeInTheDocument();
  });

  it('renders Zoom info', () => {
    render(<CornerstoneElement {...defaultProps} />);
    expect(screen.getByText(/Zoom/)).toBeInTheDocument();
  });

  it('renders WW/WC info', () => {
    render(<CornerstoneElement {...defaultProps} />);
    expect(screen.getByText(/WW\/WC/)).toBeInTheDocument();
  });

  it('renders collapsible metadata panel', () => {
    render(<CornerstoneElement {...defaultProps} />);
    expect(screen.getByText('Metadata')).toBeInTheDocument();
  });

  it('renders bottom touch toolbar with min 44px buttons', () => {
    render(<CornerstoneElement {...defaultProps} />);
    const buttons = screen.getAllByRole('button').filter(
      b => b.closest('div[style*="bottom: 0"]') || (b.style && b.style.minHeight === '44px')
    );
    expect(buttons.length).toBeGreaterThanOrEqual(4);
    buttons.forEach(btn => {
      expect(btn.style.minHeight).toBe('44px');
      expect(btn.style.minWidth).toBe('44px');
    });
  });
});
