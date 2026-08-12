import { init as csCoreInit } from "@cornerstonejs/core";
import {
  init as csToolsInit,
  ToolGroupManager,
  addTool,
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
  CobbAngleTool,
  ProbeTool,
  CircleROITool,
} from "@cornerstonejs/tools";
import { init as initDicomImageLoader } from "@cornerstonejs/dicom-image-loader";

export const ENGINE_ID = "OPENPACS_ENGINE";
export const TOOL_GROUP_ID = "OPENPACS_TOOL_GROUP";

let globalInitCalled = false;

// One-time Cornerstone3D bootstrap shared by every viewer instance. Safe to
// call concurrently from multiple mounts — the flag short-circuits the rest.
export async function ensureGlobalInit() {
  if (globalInitCalled) return;
  globalInitCalled = true;

  initDicomImageLoader({
    // IAM audit H-2: image fetches authenticate via the HttpOnly access
    // cookie, so the loader's XHR must carry credentials (WADO-RS is a
    // cross-origin fetch from the viewer origin in dev).
    beforeSend: (xhr: XMLHttpRequest) => {
      xhr.withCredentials = true;
      const tenantId = localStorage.getItem("tenant_id");
      if (tenantId) xhr.setRequestHeader("X-Tenant-ID", tenantId);
      xhr.setRequestHeader("X-CSRF-Token", "1");
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
  addTool(CobbAngleTool);
  addTool(ProbeTool);
  addTool(CircleROITool);

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
  tg.addTool(CobbAngleTool.toolName);
  tg.addTool(ProbeTool.toolName);
  tg.addTool(CircleROITool.toolName);

  // Cornerstone3D >= 5.x: `mouseButtonMask` was removed from the tool-mode
  // API — mouse bindings are expressed via `bindings`. Without an explicit
  // binding the tool flips to Active but stays inert (E2E-verified).
  tg.setToolActive(PanTool.toolName, { bindings: [{ mouseButton: 1 }] });
  tg.setToolActive(ZoomTool.toolName, { bindings: [{ mouseButton: 2 }] });
  tg.setToolActive(WindowLevelTool.toolName, {
    bindings: [{ mouseButton: 4 }],
  });
  tg.setToolActive(StackScrollTool.toolName);
}
