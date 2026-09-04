import {
  ToolGroupManager,
  PanTool,
  LengthTool,
  RectangleROITool,
  AngleTool,
  ArrowAnnotateTool,
  EllipticalROITool,
  EraserTool,
  CobbAngleTool,
  ProbeTool,
  CircleROITool,
  ZoomTool,
  WindowLevelTool,
  StackScrollTool,
} from "@cornerstonejs/tools";
import { TOOL_GROUP_ID } from "./setup";

export function getToolGroup() {
  return ToolGroupManager.getToolGroup(TOOL_GROUP_ID);
}

// Promotes a single tool to primary (left mouse) and demotes Pan, so exactly
// one annotation tool is active at a time. The `bindings` shape (not the
// legacy `mouseButtonMask`) is required by Cornerstone3D >= 5.x.
export function setPrimaryTool(toolName: string): void {
  const tg = getToolGroup();
  if (!tg) return;
  tg.setToolPassive(PanTool.toolName);
  tg.setToolActive(toolName, { bindings: [{ mouseButton: 1 }] });
}

export function activateDrag(): void {
  const tg = getToolGroup();
  if (!tg) return;
  tg.setToolPassive(ArrowAnnotateTool.toolName);
  tg.setToolPassive(AngleTool.toolName);
  tg.setToolPassive(LengthTool.toolName);
  tg.setToolPassive(RectangleROITool.toolName);
  tg.setToolPassive(EllipticalROITool.toolName);
  tg.setToolPassive(EraserTool.toolName);
  tg.setToolPassive(CobbAngleTool.toolName);
  tg.setToolPassive(ProbeTool.toolName);
  tg.setToolPassive(CircleROITool.toolName);
  tg.setToolPassive(ZoomTool.toolName);
  tg.setToolPassive(WindowLevelTool.toolName);
  tg.setToolActive(PanTool.toolName, { bindings: [{ mouseButton: 1 }] });
}

/** Promotes Window/Level to left-drag (and demotes Pan). (docs/viewer spec — W.) */
export function activateWl(): void {
  const tg = getToolGroup();
  if (!tg) return;
  tg.setToolPassive(PanTool.toolName);
  tg.setToolActive(WindowLevelTool.toolName, { bindings: [{ mouseButton: 1 }] });
}

/** Promotes Zoom to left-drag (and demotes Pan). (docs/viewer spec — Z.) */
export function activateZoom(): void {
  const tg = getToolGroup();
  if (!tg) return;
  tg.setToolPassive(PanTool.toolName);
  tg.setToolActive(ZoomTool.toolName, { bindings: [{ mouseButton: 1 }] });
}

export function activateLine(): void {
  setPrimaryTool(LengthTool.toolName);
}

export function activateRect(): void {
  setPrimaryTool(RectangleROITool.toolName);
}

export function activateElipse(): void {
  setPrimaryTool(EllipticalROITool.toolName);
}

export function activateAngle(): void {
  setPrimaryTool(AngleTool.toolName);
}

export function activateArrow(): void {
  setPrimaryTool(ArrowAnnotateTool.toolName);
}

export function activateEraser(): void {
  setPrimaryTool(EraserTool.toolName);
}

export function activateCobbAngle(): void {
  setPrimaryTool(CobbAngleTool.toolName);
}

export function activateProbe(): void {
  setPrimaryTool(ProbeTool.toolName);
}

export function activateCircleRoi(): void {
  setPrimaryTool(CircleROITool.toolName);
}
