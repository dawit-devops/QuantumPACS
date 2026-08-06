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
    // WADO-RS (and WADO-URI) requests carry the same auth headers as the
    // rest of the API — without X-Auth-Pacs the loader gets a 401 from
    // every image fetch.
    beforeSend: (xhr: XMLHttpRequest) => {
      const token = localStorage.getItem("access_token");
      if (token) xhr.setRequestHeader("X-Auth-Pacs", token);
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
