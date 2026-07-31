import {
  ToolGroupManager,
  PanTool,
  LengthTool,
  RectangleROITool,
  AngleTool,
  ArrowAnnotateTool,
  EllipticalROITool,
  EraserTool,
} from "@cornerstonejs/tools";
import { TOOL_GROUP_ID } from "./setup";

export function getToolGroup() {
  return ToolGroupManager.getToolGroup(TOOL_GROUP_ID);
}

// Promotes a single tool to primary (left mouse) and demotes Pan, so exactly
// one annotation tool is active at a time.
export function setPrimaryTool(toolName: string): void {
  const tg = getToolGroup();
  if (!tg) return;
  tg.setToolPassive(PanTool.toolName);
  (tg as any).setToolActive(toolName, { mouseButtonMask: 1 });
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
  (tg as any).setToolActive(PanTool.toolName, { mouseButtonMask: 1 });
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
