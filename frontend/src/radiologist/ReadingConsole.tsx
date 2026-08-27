import { useDocumentTitle } from "../hooks";
import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  App,
  Layout,
  Tag,
  Button,
  Space,
  Alert,
  Spin,
  Modal,
  Grid,
  Badge,
  Input,
  Form,
  Select,
  Dropdown,
} from "antd";
import {
  FileTextOutlined,
  CheckCircleOutlined,
  SaveOutlined,
  DashboardOutlined,
  RollbackOutlined,
  AlertOutlined,
  BookOutlined,
  DesktopOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  MoreOutlined,
  PictureOutlined,
} from "@ant-design/icons";
import { useParams, useNavigate, useLocation } from "react-router";
import withSidebar from "../common/base";
import { request } from "../helpers";
import { useAuth } from "../auth/AuthContext";
import { API_URL } from "../config";
import ResizableSplit from "../common/ResizableSplit";
import SeriesNavigator from "./SeriesNavigator";
import ReportPanel from "./ReportPanel";
import { useExamImaging } from "./useExamImaging";
import { useReaderShortcuts } from "./useReaderShortcuts";
import { getWeasisStatus, openInWeasis } from "../api/weasis";
import { parseAnnotations } from "../detail/MeasurementPanel";
import MeasurementPanel from "../detail/MeasurementPanel";
import { KeyboardShortcuts } from "../detail/KeyboardShortcuts";
import "./ReadingConsole.css";

const Content = Layout.Content;

const PRIORITY_COLORS: Record<string, string> = {
  stat: "red",
  urgent: "orange",
  routine: "default",
};

// NFR-R12-10: report autosave cadence ≤ 10s; drafts must never be lost.
const AUTOSAVE_MS = 3000;

// The console reuses the Cornerstone viewer unchanged — Detail mounts it by
// file id, the console mounts it with a file picked from the exam's imaging
// tree. Lazy so the report-only fallback never pulls the rendering engine.
const CornerstoneElement = React.lazy(() => import("../detail/CornerstoneElement"));

// Split reading console: viewer (left) + report (right) on one screen, with
// the full report lifecycle (autosave, templates, sign) that the old
// text-only ReportEditor had. The report pane collapses to a slim tab via
// [ / ] and the Sign action moves to the console header while collapsed.
function ReadingConsole() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Reading Console");
  const { examId } = useParams<{ examId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  // The worklist serializes its filters into the URL when opening an exam;
  // Sign & Next and Back restore them by navigating back with the same query.
  const worklistSearch = location.search;

  // REPORT_WRITE gates editing; REPORT_SIGN gates finalizing (the same
  // permission split ReportEditor applied to the text-only page). The role
  // selects the resident (submit → co-sign) vs radiologist (sign) lifecycle.
  const { user, hasPermission } = useAuth();
  const role = user?.role || "";
  const canWrite = hasPermission("REPORT_WRITE");
  const canSign = hasPermission("REPORT_SIGN");

  const screens = Grid.useBreakpoint();
  const isMobile = screens.md === false;

  const {
    exam,
    report,
    imaging,
    studies,
    selectedStudy,
    selectedSeries,
    selectedFile,
    loading,
    error,
    setReport,
    selectStudy,
    selectSeries,
    selectFile,
  } = useExamImaging(examId);

  const [templates, setTemplates] = useState<any[]>([]);
  const [findings, setFindings] = useState("");
  const [impression, setImpression] = useState("");
  const [recommendations, setRecommendations] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [status, setStatus] = useState("draft");
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [dirty, setDirty] = useState(false);
  const [signOpen, setSignOpen] = useState(false);
  const [signing, setSigning] = useState(false);
  // R-16: per-recipient ORU delivery receipts fetched after signing.
  const [distribution, setDistribution] = useState<any[] | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [returnOpen, setReturnOpen] = useState(false);
  const [returning, setReturning] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  // Viewer full-screen: the report pane is hidden and the viewport takes the
  // whole console width (independent of immersive, which only collapses the
  // sidebar). The report stays mounted underneath — toggling back restores
  // the split without losing the draft.
  const [viewerFullscreen, setViewerFullscreen] = useState(false);
  // Representative key images (2-3) captured from the live viewer and attached
  // to the report — they render inside the final document.
  const [keyImages, setKeyImages] = useState<any[]>([]);
  const [capturing, setCapturing] = useState(false);
  const [keyImagesOpen, setKeyImagesOpen] = useState(false);
  // CR-6: "Flag Critical" opens the S10 critical-results modal for the
  // exam currently loaded in the console.
  const [criticalOpen, setCriticalOpen] = useState(false);
  // R-11: teaching file submission from the console.
  const [teachOpen, setTeachOpen] = useState(false);
  const [teachSaving, setTeachSaving] = useState(false);
  const [teachForm] = Form.useForm();
  // ADR-028: show the Weasis launch action only when the connector
  // integration is enabled; a failed probe hides the button.
  const [weasisEnabled, setWeasisEnabled] = useState(false);
  useEffect(() => {
    getWeasisStatus()
      .then((s) => setWeasisEnabled(s.enabled))
      .catch(() => setWeasisEnabled(false));
  }, []);
  const [FlagCriticalModal, setFlagCriticalModal] = useState<React.ComponentType<any> | null>(null);
  useEffect(() => {
    if (!criticalOpen) return;
    import("./CriticalResults").then((m) => setFlagCriticalModal(() => m.FlagCriticalModal));
  }, [criticalOpen]);

  // The same filtered queue the worklist shows, fetched so Sign & Next can
  // jump straight to the next unread exam instead of round-tripping through
  // the worklist. Filters come from the URL the worklist serialized on open.
  const [queue, setQueue] = useState<any[]>([]);
  const queueQuery = useMemo(() => {
    const q: Record<string, string> = {};
    const sp = new URLSearchParams(location.search);
    for (const k of ["status", "modality", "search", "radiologist", "physician"]) {
      const v = sp.get(k);
      if (v) q[k] = v;
    }
    return q;
  }, [location.search]);

  // Viewer-side annotation state, mirroring Detail's wiring.
  const [rawAnnotations, setRawAnnotations] = useState<any[]>([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const [focusAnnotationUID, setFocusAnnotationUID] = useState<string | null>(null);

  // Load the queue once with the console (mirroring the worklist's filters);
  // Sign & Next consumes it. Failures are non-fatal — Sign & Next degrades
  // to returning to the worklist.
  useEffect(() => {
    request("reports/reading-list", { query: queueQuery })
      .then((res: any) => setQueue(Array.isArray(res.data) ? res.data : []))
      .catch(() => setQueue([]));
  }, [queueQuery]);

  // Load representative key images for this exam.
  useEffect(() => {
    if (!examId) return;
    request(`reports/${examId}/key-images`)
      .then((res: any) => setKeyImages(Array.isArray(res.data) ? res.data : []))
      .catch(() => setKeyImages([]));
  }, [examId]);

  const captureKeyImage = async () => {
    const canvas = document.querySelector(".viewportElement canvas") as HTMLCanvasElement | null;
    if (!canvas) return;
    setCapturing(true);
    try {
      const dataUrl = canvas.toDataURL("image/png");
      await request(`reports/${examId}/key-images`, {
        method: "POST",
        data: { image_data: dataUrl },
      });
      const res = await request(`reports/${examId}/key-images`);
      setKeyImages(Array.isArray(res.data) ? res.data : []);
    } catch (e: any) {
      message?.error?.(e.message || "Failed to capture key image");
    } finally {
      setCapturing(false);
    }
  };

  const removeKeyImage = async (imageId: number) => {
    try {
      await request(`reports/${examId}/key-images/${imageId}`, { method: "DELETE" });
      setKeyImages((prev) => prev.filter((k) => k.id !== imageId));
    } catch (e: any) {
      message?.error?.(e.message || "Failed to remove key image");
    }
  };

  const saveTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  // The autosave interval is registered once; read the live dirty flag AND the
  // latest saveDraft via refs so the interval closure never sees a stale value
  // (NFR-R12-10 — zero drafts lost). The status ref stops the loop from
  // hammering a submitted report, which the backend rejects as locked.
  const dirtyRef = useRef(false);
  const statusRef = useRef(status);
  const saveDraftRef = useRef<() => void>(() => {});

  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  // Seed the editing state from the loaded report (once — later report
  // updates, e.g. the signed record, re-sync status/savedAt).
  useEffect(() => {
    if (!report) return;
    setFindings(report.findings || "");
    setImpression(report.impression || "");
    setRecommendations(report.recommendations || "");
    setTemplateName(report.template_name || "");
    setStatus(report.status || "draft");
    setSavedAt(report.updated_at ? new Date(report.updated_at) : null);
  }, [report]);

  useEffect(() => {
    request("reports/templates", {
      query: { modality: exam?.modality || "" },
    })
      .then((res: any) => setTemplates(Array.isArray(res.data) ? res.data : []))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exam?.modality]);

  const saveDraft = useCallback(
    async (silent = true, explicitStatus?: string): Promise<boolean> => {
      // Read-only viewers never save: the guard also makes the autosave
      // interval a no-op for them.
      if (!canWrite) return true;
      dirtyRef.current = false;
      setDirty(false);
      try {
        await request(`reports/${examId}`, {
          // ExamReportHandler only implements GET/PUT — POST returns 405
          method: "PUT",
          data: {
            findings,
            impression,
            recommendations,
            template_name: templateName,
            status:
              // CR-4: the backend rejects `final` and locks signed reports —
              // autosave only ever sends draft/preliminary, never a flip from
              // final (which previously 400'd and triggered retry loops).
              explicitStatus ?? (status === "final" ? "draft" : status),
          },
        });
        setSavedAt(new Date());
        if (!silent) message?.success?.("Draft saved");
        return true;
      } catch (e: any) {
        // Never lose the draft on a transient failure — mark dirty again so
        // the autosave loop retries (NFR-R12-10).
        dirtyRef.current = true;
        setDirty(true);
        if (!silent) message?.error?.(e.message || "Save failed");
        return false;
      }
    },
    [canWrite, examId, findings, impression, recommendations, status, templateName]
  );

  // Keep the interval closure pointing at the latest saveDraft after every render.
  useEffect(() => {
    saveDraftRef.current = () => saveDraft();
  });

  useEffect(() => {
    // Autosave loop: flush the local draft on an interval (FR-R12-09 /
    // NFR-R12-10).
    saveTimer.current = setInterval(() => {
      if (dirtyRef.current && statusRef.current !== "submitted" && statusRef.current !== "final") {
        saveDraftRef.current();
      }
    }, AUTOSAVE_MS);
    return () => {
      if (saveTimer.current) clearInterval(saveTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyTemplate = (name: string) => {
    const t = templates.find((x) => x.name === name);
    if (!t) return;
    setFindings(t.findings_template || "");
    setImpression(t.impression_template || "");
    setRecommendations("");
    setTemplateName(name);
    dirtyRef.current = true;
    setDirty(true);
    message.info(`Template "${name}" applied`);
  };

  const markPreliminary = () => {
    setStatus("preliminary");
    // Pass the explicit status: setStatus only affects the UI, and the
    // saveDraft closure still carries the previous status in this render.
    saveDraft(true, "preliminary").then(() => message?.success?.("Marked preliminary"));
  };

  const goBack = () => {
    navigate(`/reading${worklistSearch}`);
  };

  // The next exam to read after this one: the item after the current exam in
  // the filtered queue (STAT→urgent→routine, FIFO within tier — the same
  // order the worklist sorts). The queue excludes final-signed exams, so the
  // next item is by construction unread. Falls back to the worklist when the
  // queue is exhausted or failed to load.
  const nextExamId = useCallback((): string | null => {
    const idx = queue.findIndex((item) => item.exam_id === examId);
    if (idx >= 0) return queue[idx + 1]?.exam_id ?? null;
    return queue[0]?.exam_id ?? null;
  }, [queue, examId]);

  // §5.2 ← / → in immersive mode walk the same queue backwards/forwards.
  const prevExamId = useCallback((): string | null => {
    const idx = queue.findIndex((item) => item.exam_id === examId);
    if (idx > 0) return queue[idx - 1].exam_id;
    return null;
  }, [queue, examId]);

  const navigateExam = useCallback(
    (id: string | null) => {
      if (id) navigate(`/reading/${id}${worklistSearch}`);
    },
    [navigate, worklistSearch]
  );

  // R-06: restore a prior version — the server copies the snapshot onto the
  // report (appending a new version); we then reload it into the console.
  const restoreVersion = useCallback(
    async (version: number) => {
      if (!report?.id) return;
      try {
        await request(`reports/${report.id}/versions/${version}/restore`, {
          method: "POST",
          data: undefined,
        });
        const res = await request(`reports/${examId}`);
        const r = res?.data?.report ?? null;
        setReport(r);
        setFindings(r?.findings || "");
        setImpression(r?.impression || "");
        setRecommendations(r?.recommendations || "");
        dirtyRef.current = false;
        setDirty(false);
        message?.success?.(`Version ${version} restored`);
      } catch (e: any) {
        message?.error?.(e.message || "Restore failed");
      }
    },
    [report?.id, examId, setReport, message]
  );

  // R-11: submit the current case to the teaching file library.
  const submitTeachingFile = async () => {
    try {
      const values = await teachForm.validateFields();
      setTeachSaving(true);
      await request("teaching-files", {
        method: "POST",
        data: {
          exam_id: examId,
          title: values.title,
          diagnosis: values.diagnosis || "",
          difficulty: values.difficulty || "medium",
          teaching_points: (values.teaching_points || "")
            .split("\n")
            .map((s: string) => s.trim())
            .filter(Boolean),
          differential_diagnosis: (values.differential_diagnosis || "")
            .split("\n")
            .map((s: string) => s.trim())
            .filter(Boolean),
        },
      });
      message?.success?.("Case submitted to the teaching library");
      setTeachOpen(false);
      teachForm.resetFields();
    } catch (e: any) {
      if (e?.errorFields) return; // form validation, modal stays open
      message?.error?.(e.message || "Teaching file submission failed");
    } finally {
      setTeachSaving(false);
    }
  };

  const signReport = async (next: boolean) => {
    if (!impression.trim()) {
      message?.error?.("Impression is required before signing");
      return;
    }
    setSigning(true);
    try {
      // Flush any pending edits first, then sign. Abort the sign if the
      // flush failed so we never finalize a report missing the last
      // keystrokes. A submitted report is already persisted and locked —
      // flushing would PUT into a guard that rejects it.
      const wasSubmitted = status === "submitted";
      const saved = wasSubmitted ? true : await saveDraft(true);
      if (!saved) {
        message?.error?.("Could not save the draft — sign aborted. Try again.");
        return;
      }
      const res = await request(`reports/${examId}/sign`, {
        data: { confirm: true },
      });
      setReport(res.data);
      setStatus("final");
      setSavedAt(new Date());
      setSignOpen(false);
      if (next) {
        // R-15: Sign & Next names the patient coming up so the radiologist
        // knows where the queue is taking them next.
        const nextId = nextExamId();
        const nextName = nextId
          ? queue.find((item) => item.exam_id === nextId)?.patient_name
          : null;
        message?.success?.(
          nextName
            ? `Report signed ✓ — Next: ${nextName}`
            : nextId
              ? "Report signed ✓ — Next: study"
              : "Report signed ✓ — queue complete"
        );
        // Sign & next: jump to the next unread exam in the same filtered
        // queue, preserving the worklist filters for the next console. When
        // the queue is empty (or unknown) return to the worklist instead.
        navigate(nextId ? `/reading/${nextId}${worklistSearch}` : `/reading${worklistSearch}`);
      } else {
        message?.success?.(
          wasSubmitted
            ? "Report co-signed — status is now FINAL"
            : "Report signed — status is now FINAL"
        );
        // R-16: distribution confirmation — receipt rows from the ORU engine.
        if (res.data?.id) {
          request(`notifications/delivery-status?report_id=${res.data.id}`)
            .then((d: any) => setDistribution(Array.isArray(d.data) ? d.data : []))
            .catch(() => setDistribution([]));
        }
      }
    } catch (e: any) {
      message?.error?.(e.message || "Sign failed");
    } finally {
      setSigning(false);
    }
  };

  // R13 resident submit: flush the latest keystrokes, then hand the draft to
  // the supervising attending. Once submitted the report locks (the backend
  // rejects further PUTs) until co-signed or returned.
  const submitReport = async () => {
    if (!impression.trim()) {
      message?.error?.("Impression is required before submitting for review");
      return;
    }
    setSubmitting(true);
    try {
      const saved = await saveDraft(true);
      if (!saved) {
        message?.error?.("Could not save the draft — submit aborted. Try again.");
        return;
      }
      const res = await request(`reports/${examId}/submit`, { method: "POST" });
      setReport(res.data);
      setStatus("submitted");
      dirtyRef.current = false;
      setDirty(false);
      setSavedAt(new Date());
      message?.success?.("Report submitted for attending review");
    } catch (e: any) {
      message?.error?.(e.message || "Submit failed");
    } finally {
      setSubmitting(false);
    }
  };

  // Attending return: reopen the resident's submitted draft with feedback
  // attached — their console surfaces it so they know what to revise.
  const returnReport = async () => {
    if (!feedback.trim()) {
      message?.error?.("Feedback is required before returning the report");
      return;
    }
    setReturning(true);
    try {
      const res = await request(`reports/${examId}/return`, {
        method: "POST",
        data: { feedback, confirm: true },
      });
      setReport(res.data);
      setStatus("draft");
      setSavedAt(new Date());
      setReturnOpen(false);
      setFeedback("");
      message?.success?.("Report returned to the resident for revision");
    } catch (e: any) {
      message?.error?.(e.message || "Return failed");
    } finally {
      setReturning(false);
    }
  };

  // [ / ] collapses/expands the report pane. Shares the focus guard the
  // viewer uses: never steal keys inside inputs, antd overlays, or dialogs.
  // §5 immersive reader mode + global shortcut map (declared after every
  // handler it closes over).
  const { immersive, toggleImmersive } = useReaderShortcuts({
    saveDraft: () => {
      saveDraft(false);
    },
    requestSign: () => setSignOpen(true),
    submitReport,
    goPrevExam: () => navigateExam(prevExamId()),
    goNextExam: () => navigateExam(nextExamId()),
    goToWorklist: goBack,
    showHelp: () => setShowShortcuts(true),
  });

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "[" && e.key !== "]") return;
      const target = e.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
      const inOverlay = !!document.activeElement?.closest(
        ".ant-select, .ant-drawer, .ant-collapse, [role='dialog'], [role='menu']"
      );
      if (isInput || inOverlay) return;
      e.preventDefault();
      setCollapsed(e.key === "[");
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  // Single-page reading room: the console must fit one viewport (no page
  // scroll) — the viewer and the report editor share the height, so the
  // app chrome (.page-content) must clamp to the window instead of growing
  // with its content. Body-scoped like immersive mode so other routes keep
  // normal scrolling.
  useEffect(() => {
    document.body.classList.add("reading-console-single");
    return () => document.body.classList.remove("reading-console-single");
  }, []);

  const handleAnnotationsChange = useCallback((annotations: any[]) => {
    setRawAnnotations(annotations || []);
  }, []);

  const handleFocusAnnotation = useCallback((annotationUID: string) => {
    setFocusAnnotationUID(annotationUID);
    setTimeout(() => setFocusAnnotationUID(null), 100);
  }, []);

  const imageUrl = selectedFile ? `wadouri:${API_URL}/files/${selectedFile.id}/data` : "";
  const files = selectedSeries?.files ?? [];
  const fileIndex = files.findIndex((f) => f.id === selectedFile?.id);
  const measurements = parseAnnotations(rawAnnotations, imageUrl);

  // CornerstoneElement's `file` prop — the tree node enriched with the
  // series modality (reading presets) and patient context (metadata panel).
  const ceFile = selectedFile
    ? {
        ...selectedFile,
        modality: selectedSeries?.modality || "",
        patient: exam ? { name: exam.patient_name, patient_id: exam.patient_id } : undefined,
        study: selectedStudy?.description || selectedStudy?.study_id || "",
        series: selectedSeries?.description || String(selectedSeries?.number ?? ""),
      }
    : { id: 0 };

  const viewportPane = (
    <div className="reading-viewport-pane">
      <div className="reading-viewport-tools">
        <SeriesNavigator
          studies={studies}
          selectedStudy={selectedStudy}
          selectedSeries={selectedSeries}
          fileIndex={Math.max(0, fileIndex)}
          files={files}
          onStudyChange={selectStudy}
          onSeriesChange={selectSeries}
          onFileChange={selectFile}
        />
        <Button
          size="small"
          onClick={() => setPanelOpen(!panelOpen)}
          aria-expanded={panelOpen}
          className="reading-measures-toggle"
        >
          <Badge count={measurements.length} size="small" offset={[2, -4]}>
            <DashboardOutlined />
          </Badge>
          Measures
        </Button>
        <Button
          size="small"
          onClick={() => setKeyImagesOpen(true)}
          aria-expanded={keyImagesOpen}
          title="Representative key images for the report"
        >
          <Badge count={keyImages.length} size="small" offset={[2, -4]}>
            <PictureOutlined />
          </Badge>
          Key images
        </Button>
      </div>
      <div className="reading-viewport-body">
        <div className="reading-viewport-main">
          {selectedFile ? (
            <Suspense
              fallback={
                <Spin
                  size="large"
                  style={{
                    display: "flex",
                    justifyContent: "center",
                    marginTop: 100,
                  }}
                />
              }
            >
              <CornerstoneElement
                file={ceFile}
                files={files}
                changeFile={selectFile}
                image={imageUrl}
                progressive={true}
                visible
                onRequestHelp={() => setShowShortcuts(true)}
                onAnnotationsChange={handleAnnotationsChange}
                focusAnnotationUID={focusAnnotationUID}
                isMobile={isMobile}
                enableReadingPresets={hasPermission("REPORT_READ")}
              />
            </Suspense>
          ) : (
            <Alert type="info" showIcon title="No images in this series" style={{ margin: 16 }} />
          )}
        </div>
        <MeasurementPanel
          measurements={measurements}
          onFocusAnnotation={handleFocusAnnotation}
          collapsed={!panelOpen}
          onToggle={() => setPanelOpen(false)}
          visible
        />
      </div>
    </div>
  );

  const reportContent = (
    <ReportPanel
      exam={exam}
      report={report}
      role={role}
      canWrite={canWrite}
      canSign={canSign}
      status={status}
      findings={findings}
      impression={impression}
      recommendations={recommendations}
      templates={templates}
      dirty={dirty}
      reviewFeedback={report?.review_feedback}
      distribution={distribution}
      onFindingsChange={(v) => {
        setFindings(v);
        dirtyRef.current = true;
        setDirty(true);
      }}
      onImpressionChange={(v) => {
        setImpression(v);
        dirtyRef.current = true;
        setDirty(true);
      }}
      onRecommendationsChange={(v) => {
        setRecommendations(v);
        dirtyRef.current = true;
        setDirty(true);
      }}
      onApplyTemplate={applyTemplate}
      onSaveDraft={() => saveDraft(false)}
      onRestoreVersion={restoreVersion}
      onMarkPreliminary={markPreliminary}
      onSubmitDraft={submitReport}
      onRequestSign={() => setSignOpen(true)}
      onReturnClick={() => setReturnOpen(true)}
    />
  );

  const reportPane = collapsed ? (
    <button
      type="button"
      className="reading-report-tab"
      onClick={() => setCollapsed(false)}
      aria-label="Expand report panel"
    >
      <FileTextOutlined /> Report
    </button>
  ) : (
    <div className="reading-report-pane">{reportContent}</div>
  );

  const isFinal = status === "final";

  return (
    <Content
      className={`reading-console${immersive ? " immersive" : ""}`}
      style={{
        padding: 24,
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
      }}
      role="main"
    >
      {exam && (
        <header className="reading-console-header">
          <Button onClick={goBack} className="report-back">
            ← Back to worklist
          </Button>
          <div className="reading-console-header-title">
            <h2>
              <FileTextOutlined /> Report — {exam.accession_number || exam.id.slice(0, 8)}
              <Tag
                color={PRIORITY_COLORS[exam.priority]}
                className={exam.priority === "stat" ? "report-stat-tag" : undefined}
              >
                {(exam.priority || "routine").toUpperCase()}
              </Tag>
              <Tag
                color={
                  isFinal
                    ? "green"
                    : status === "preliminary"
                      ? "purple"
                      : status === "submitted"
                        ? "cyan"
                        : "gold"
                }
              >
                {status.toUpperCase()}
              </Tag>
            </h2>
            <span className="reading-console-subtitle">
              {exam.patient_name || exam.patient_id} · {exam.modality} ·{" "}
              {exam.protocol_name || "No protocol"}
            </span>
          </div>
          <Space wrap>
            {savedAt && (
              <span className="reading-console-saved">
                <SaveOutlined /> {savedAt.toLocaleTimeString()}
              </span>
            )}
            {/* §5.1 manual immersive toggle (Space also toggles). Collapses
                the sidebar to icon-only and darkens the reading room. */}
            <Button size="small" aria-pressed={immersive} onClick={toggleImmersive}>
              {immersive ? "Exit immersive" : "Immersive"}
            </Button>
            {/* Viewer full-screen: expand the viewport to the whole console
                width, hiding the report pane (the draft stays mounted). */}
            <Button
              size="small"
              aria-pressed={viewerFullscreen}
              onClick={() => setViewerFullscreen((v) => !v)}
              title={viewerFullscreen ? "Exit viewer full-screen" : "Full-screen viewer"}
            >
              {viewerFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            </Button>
            {/* ADR-028: launch the loaded study in the Weasis web viewer — the
                study the exam's imaging tree selected (the DICOMweb console in
                StudyBrowser does the same). The backend re-checks
                DICOMWEB_READ on /weasis/launch. */}
            {weasisEnabled && selectedStudy?.study_instance_uid && (
              <Button
                size="small"
                icon={<DesktopOutlined />}
                onClick={() => openInWeasis(selectedStudy.study_instance_uid!)}
              >
                Weasis
              </Button>
            )}
            {/* Sign stays in the header so it remains reachable while the
                report pane is collapsed ([). A submitted report swaps the
                sign affordance for the attending's review pair: co-sign or
                return. */}
            {!isFinal && canSign && status === "submitted" && (
              <>
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={() => setSignOpen(true)}
                >
                  Co-sign
                </Button>
                <Button icon={<RollbackOutlined />} onClick={() => setReturnOpen(true)}>
                  Return
                </Button>
              </>
            )}
            {!isFinal && canSign && status !== "submitted" && (
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => setSignOpen(true)}
              >
                Sign Report
              </Button>
            )}
            {/* Secondary actions condensed into a More menu so the header
                stays one row and the viewer/editor keep the vertical space. */}
            {(canWrite && report) || canWrite ? (
              <Dropdown
                trigger={["click"]}
                menu={{
                  items: [
                    ...(canWrite && report
                      ? [
                          {
                            key: "critical",
                            icon: <AlertOutlined />,
                            label: "Flag Critical",
                            onClick: () => setCriticalOpen(true),
                          },
                        ]
                      : []),
                    ...(canWrite
                      ? [
                          {
                            key: "teaching",
                            icon: <BookOutlined />,
                            label: "Submit to Teaching File",
                            onClick: () => setTeachOpen(true),
                          },
                        ]
                      : []),
                  ],
                }}
              >
                <Button size="small" aria-label="More actions" icon={<MoreOutlined />} />
              </Dropdown>
            ) : null}
          </Space>
        </header>
      )}

      {/* R-11: submit this case to the teaching file library. */}
      <Modal
        title="Submit to Teaching File"
        open={teachOpen}
        onCancel={() => setTeachOpen(false)}
        onOk={submitTeachingFile}
        confirmLoading={teachSaving}
        okText="Submit case"
      >
        <Form form={teachForm} layout="vertical">
          <Form.Item
            name="title"
            label="Case title"
            rules={[{ required: true, message: "A title is required" }]}
          >
            <Input placeholder="e.g. Classic subdural hematoma" />
          </Form.Item>
          <Form.Item name="diagnosis" label="Teaching diagnosis">
            <Input placeholder="Primary diagnosis" />
          </Form.Item>
          <Form.Item name="difficulty" label="Difficulty" initialValue="medium">
            <Select
              options={["easy", "medium", "hard"].map((d) => ({
                value: d,
                label: d,
              }))}
            />
          </Form.Item>
          <Form.Item name="teaching_points" label="Teaching points (one per line)">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="differential_diagnosis" label="Differential diagnosis (one per line)">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {FlagCriticalModal && (
        <FlagCriticalModal
          visible={criticalOpen}
          exam={exam}
          report={report}
          onClose={() => setCriticalOpen(false)}
          onSuccess={() => {}}
        />
      )}

      {/* Representative key images (2-3) captured from the live viewer —
          rendered inside the final report document. */}
      <Modal
        title="Representative Key Images"
        open={keyImagesOpen}
        onCancel={() => setKeyImagesOpen(false)}
        footer={null}
        width={480}
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          title="Capture up to 3 images from the live viewer"
          description="Use the 'Capture current view' button below, then Sign to include them in the final report."
        />
        <div className="reading-key-images-grid">
          {keyImages.map((img, i) => (
            <div key={img.id} className="reading-key-image-card">
              <div className="reading-key-image-index"># {i + 1}</div>
              <img src={img.dataUrl || ""} alt={img.caption || `Key image ${i + 1}`} />
              <Button
                type="text"
                danger
                size="small"
                onClick={() => removeKeyImage(img.id)}
                disabled={!canWrite}
              >
                Remove
              </Button>
            </div>
          ))}
        </div>
        {keyImages.length === 0 && (
          <p style={{ color: "var(--text-secondary, #8c8c8c)" }}>
            No key images yet — capture one from the viewer.
          </p>
        )}
        <div className="report-actions">
          <Button
            type="primary"
            icon={<PictureOutlined />}
            loading={capturing}
            onClick={captureKeyImage}
            disabled={!canWrite || keyImages.length >= 3}
          >
            Capture current view
          </Button>
        </div>
      </Modal>

      {loading && !exam ? (
        <div className="report-loading">
          <Spin size="large" />
        </div>
      ) : error && !exam ? (
        <div>
          <Alert type="error" title="Failed to load exam" description={error} showIcon />
          <Button style={{ marginTop: 12 }} onClick={goBack}>
            Back to worklist
          </Button>
        </div>
      ) : !exam ? null : imaging ? (
        isMobile ? (
          <div className="reading-console-mobile">
            <div className="reading-console-mobile-viewport" style={{ minHeight: "55vh" }}>
              {viewportPane}
            </div>
            <div className="reading-console-mobile-report">{reportContent}</div>
          </div>
        ) : viewerFullscreen ? (
          // Viewer full-screen: the viewport spans the whole console width.
          // The report pane stays mounted (hidden) so toggling back restores
          // the split without losing the draft.
          <div className="reading-console-fullscreen">{viewportPane}</div>
        ) : (
          <ResizableSplit
            storageKey="reading-console-split"
            left={viewportPane}
            right={reportPane}
            ariaLabel="Resize report panel"
          />
        )
      ) : (
        <div className="reading-console-full">
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            title="No imaging available"
            description="No DICOM study matched this exam yet. The report is shown in full width — images will appear here once the study is stored."
          />
          {reportContent}
        </div>
      )}

      <Modal
        title={status === "submitted" ? "Approve & Co-sign" : "Sign Report"}
        open={signOpen}
        onCancel={() => setSignOpen(false)}
        okText="Sign & Finalize"
        okButtonProps={{ loading: signing, disabled: !impression.trim() }}
        destroyOnHidden
        footer={[
          <Button key="cancel" onClick={() => setSignOpen(false)}>
            Cancel
          </Button>,
          <Button
            key="next"
            type="primary"
            loading={signing}
            disabled={!impression.trim()}
            onClick={() => signReport(true)}
          >
            Sign & Next
          </Button>,
          <Button
            key="finalize"
            disabled={!impression.trim()}
            loading={signing}
            onClick={() => signReport(false)}
          >
            Sign & Finalize
          </Button>,
        ]}
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          title={
            status === "submitted"
              ? "Co-signing finalizes the resident's submitted report as FINAL and records you as the signing radiologist."
              : "Signing makes this report FINAL and records you as the signing radiologist."
          }
        />
        <p>
          Impression preview: <em>{impression || "(empty — required to sign)"}</em>
        </p>
      </Modal>

      <Modal
        title="Return Report for Revision"
        open={returnOpen}
        onCancel={() => setReturnOpen(false)}
        onOk={returnReport}
        okText="Return & Reopen Draft"
        okButtonProps={{ loading: returning, disabled: !feedback.trim() }}
        destroyOnHidden
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title="The report reopens as an editable draft for the resident, with your feedback attached."
        />
        <Input.TextArea
          rows={4}
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="What should the resident revise? (required)"
        />
      </Modal>

      <KeyboardShortcuts open={showShortcuts} onClose={() => setShowShortcuts(false)} />

      {immersive && (
        <div className="reading-status-bar" data-testid="reader-status-bar">
          <span>Space immersive</span>
          <span>[ ] report</span>
          <span>Ctrl+S save</span>
          <span>Ctrl+Enter sign</span>
          <span>Ctrl+Shift+S submit</span>
          <span>←/→ exam</span>
          <span>Ctrl+Shift+W worklist</span>
          <span>F1 help</span>
        </div>
      )}
    </Content>
  );
}

export default withSidebar(ReadingConsole);
