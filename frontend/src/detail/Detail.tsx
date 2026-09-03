import { useDocumentTitle } from "../hooks";
import React, { Suspense, useState, useEffect, useCallback } from "react";
import { Link, useParams, useNavigate } from "react-router";
import { App, Layout, Menu, Breadcrumb, Grid, Spin, Badge, Tooltip, Radio } from "antd";
import {
  EyeOutlined,
  TableOutlined,
  ShareAltOutlined,
  HistoryOutlined,
  LockOutlined,
  DashboardOutlined,
  DesktopOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import { useTheme } from "../common/ThemeProvider";
import { KeyboardShortcuts } from "./KeyboardShortcuts";
import { parseAnnotations } from "./MeasurementPanel";
import MeasurementPanel from "./MeasurementPanel";
import { PageState } from "../common/PageState";
import PageHeader from "../common/PageHeader";
import withSidebar from "../common/base";

const { useBreakpoint } = Grid;
import {
  getFile,
  type FileRecord,
  type FileStudy,
  type FileSeries,
  type FileNode,
} from "../api/files";
import { useAuth } from "../auth/AuthContext";
import { VIEWER_ROUTE_PERMISSIONS } from "../auth/PermissionRoute";
import { isAdminScopedRole } from "../navigator";
import { API_URL } from "../config";
import { getWeasisStatus, openInWeasis } from "../api/weasis";
import { prepareWadoRsImage, wadorsRenderEnabled } from "./wadors";
const CornerstoneElement = React.lazy(() => import("./CornerstoneElement"));
const StudyCompare = React.lazy(() => import("./viewer/StudyCompare"));
import KeyValueTable from "./KeyValueTable";
import Changes from "./Changes";
import Share from "./Share";
import Management from "./Management";
import "./Detail.css";

const Content = Layout.Content;

function wrap(txt: string) {
  if (!txt) return "";
  return `(${txt})`;
}

function Detail() {
  const { message } = App.useApp();
  useDocumentTitle("QuantumPACS - Detail");
  const navigate = useNavigate();
  const params = useParams();
  const imagePath = `wadouri:${API_URL}/files/${params.id}/data`;
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const { hasPermission, user } = useAuth();
  // Viewer-level scope (route gate is the first line of defense; this covers
  // direct component reuse where no PermissionRoute wraps the mount point).
  const canViewFiles = VIEWER_ROUTE_PERMISSIONS.some((p) => hasPermission(p));
  // Admin-scoped roles keep the viewer for file verification, but the
  // clinical reading tooling around it (annotations, presets) and patient
  // navigation are trimmed — patients/ is a clinical surface for them.
  const isAdminScoped = isAdminScopedRole(user?.role);

  const [tab, setTab] = useState("image");
  const [data, setData] = useState<FileRecord>({ id: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [study, setStudy] = useState<FileStudy | null>(null);
  const [series, setSeries] = useState<FileSeries | null>(null);
  const [image, setImage] = useState(imagePath);
  const tempKey = sessionStorage.getItem("tempKey");
  const [showShortcuts, setShowShortcuts] = useState(false);

  const [rawAnnotations, setRawAnnotations] = useState<any[]>([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const [focusAnnotationUID, setFocusAnnotationUID] = useState<string | null>(null);
  const [weasisEnabled, setWeasisEnabled] = useState(false);

  // R-12: Multi-study comparison mode.
  const [compareMode, setCompareMode] = useState(false);
  const [compareLayout, setCompareLayout] = useState<"2x1" | "2x2">("2x1");
  const [priorStudyUid, setPriorStudyUid] = useState<string | null>(null);
  const [priorStudies, setPriorStudies] = useState<
    Array<{ uid: string; description: string; date: string }>
  >([]);

  // ADR-028: show the Weasis launch action only when the connector
  // integration is enabled; a failed probe hides the button.
  useEffect(() => {
    getWeasisStatus()
      .then((s) => setWeasisEnabled(s.enabled))
      .catch(() => setWeasisEnabled(false));
  }, []);

  // Pixels come from the self-contained wadouri loader (`wadouri:/files/{id}/data`)
  // by default: the v5 dicom-image-loader naturalized path parses the served
  // file and registers every metadata module (IMAGE_PIXEL included) itself, so
  // no separate metadata fetch is needed.
  //
  // F6.6a adds an opt-in WADO-RS path (localStorage `qpx.viewer.wadors=1`):
  // the instance's /metadata dicom+json document is registered into the
  // loader's metaDataManager and the wadors: imageId is rendered instead.
  // The backend WADO-RS multipart response now carries a transfer-syntax
  // Content-Type parameter per PS3.18 §11.4.1 (required for the loader to
  // pick the stored Explicit VR LE decoding path). Any failure — missing
  // UIDs, metadata fetch error, permission gap — falls back to wadouri, so
  // the option can never brick the viewer.
  const imageUrl = image;

  const measurements = parseAnnotations(rawAnnotations, imageUrl);

  const handleAnnotationsChange = useCallback((annotations: any[]) => {
    setRawAnnotations(annotations || []);
  }, []);

  const handleFocusAnnotation = useCallback((annotationUID: string) => {
    setFocusAnnotationUID(annotationUID);
    setTimeout(() => setFocusAnnotationUID(null), 100);
  }, []);

  // Resolve the pixel source for the currently open file. Default: wadouri.
  // F6.6a: when enabled, try WADO-RS (metadata registration + wadors imageId)
  // and degrade to wadouri on any failure.
  const resolvePixelSource = useCallback(
    async (
      file: FileRecord,
      curStudy: FileStudy | null,
      curSeries: FileSeries | null,
    ): Promise<string> => {
      const wadouri = `wadouri:${API_URL}/files/${file.id}/data`;
      if (
        !wadorsRenderEnabled() ||
        !curStudy?.study_instance_uid ||
        !curSeries?.series_instance_uid
      ) {
        return wadouri;
      }
      const node = (curSeries.files ?? []).find((f) => f.id === file.id);
      if (!node?.sop_instance_uid) {
        return wadouri;
      }
      try {
        return await prepareWadoRsImage(
          curStudy.study_instance_uid,
          curSeries.series_instance_uid,
          node.sop_instance_uid,
        );
      } catch {
        return wadouri;
      }
    },
    [],
  );

  useEffect(() => {
    // Do not fetch the study without viewer perms: the DICOM payload itself
    // is the protected resource, so mounting the viewer must not pull it.
    if (!canViewFiles) return;
    setLoading(true);
    setError(null);
    const { id } = params;

    getFile(id as string)
      .then((data: FileRecord) => {
        // Mount the viewer only once all metadata is in place: the remount
        // hack below used to force a second mount because the viewer could
        // initialize with empty props. CornerstoneElement now mounts
        // after-metadata and its checkReady loop covers engine readiness.
        let curStudy: FileStudy | null = null;
        let curSeries: FileSeries | null = null;
        for (const s of data.patient?.studies ?? []) {
          if (s.id === data.study_db_id) {
            curStudy = s;
            for (const sr of s.series ?? []) {
              if (sr.id === data.series_db_id) {
                curSeries = sr;
              }
            }
          }
        }
        setStudy(curStudy);
        setSeries(curSeries);
        setData(data);
        return resolvePixelSource(data, curStudy, curSeries);
      })
      .then((img: string) => {
        setImage(img);
        setLoading(false);
      })
      .catch((e: Error) => {
        setLoading(false);
        let msg = "File fail to load";
        if (e.message === "404") {
          msg = "File not found";
        }
        setError(msg);
        message.error(msg);
        if (e.message === "404") {
          navigate("/");
        }
      });
    // eslint-disable-next-line
  }, [params.id]);

  const background = tab === "image" ? "var(--viewer-bg)" : "";

  const changeStudy = (s: FileStudy) => {
    setStudy(s);
    setSeries(s.series?.[0] ?? null);
  };

  // (R1-05) Breadcrumb drop items use the native `title` + `onClick` contract
  // instead of the old `<a href="">` labels — an empty href is an invalid
  // link target and is not keyboard-activatable.
  const studiesDrop = (data: FileStudy[] | undefined) => {
    if (!data) return [];
    return data.map((d: FileStudy) => ({
      key: d.study_id,
      title: `Study ${d.study_id ?? ""} ${wrap(d.description ?? "")}`,
      onClick: () => changeStudy(d),
    }));
  };

  const changeSeries = (s: FileSeries) => {
    setSeries(s);
  };

  const seriesDrop = (data: FileSeries[] | undefined) => {
    if (!data) return [];
    return data.map((d: FileSeries) => ({
      key: d.number,
      title: `Series ${d.number ?? ""} ${wrap(d.description ?? "")}`,
      onClick: () => changeSeries(d),
    }));
  };

  const filesDrop = (data: FileNode[] | undefined) => {
    if (!data) return [];
    return data.map((d: FileNode) => ({
      key: d.id,
      label: <Link to={`/files/${d.id}`}>{`File ${d.name}`}</Link>,
    }));
  };

  if (!canViewFiles) {
    return (
      <Content style={{ alignItems: "center", justifyContent: "center" }}>
        <PageState error="You don't have access to this image" empty={false} />
      </Content>
    );
  }

  return (
    <Content
      style={{
        alignItems: "center",
        justifyContent: "center",
        background: background,
      }}
    >
      <PageState loading={loading && !data.id} error={error}>
        <PageHeader
          title={data.name ? String(data.name) : "Study Viewer"}
          description="DICOM image review"
        />
        <Menu
          style={{ paddingLeft: "40px" }}
          defaultSelectedKeys={[tab]}
          mode="horizontal"
          items={[
            {
              key: "image",
              icon: <EyeOutlined />,
              label: "Image",
              onClick: () => setTab("image"),
            },
            {
              key: "data",
              icon: <TableOutlined />,
              label: "Data",
              onClick: () => setTab("data"),
            },
            ...(!tempKey
              ? [
                  {
                    key: "share",
                    icon: <ShareAltOutlined />,
                    label: "Share",
                    onClick: () => setTab("share"),
                  },
                ]
              : []),
            ...(!tempKey
              ? [
                  {
                    key: "changes",
                    icon: <HistoryOutlined />,
                    label: "Changes",
                    onClick: () => setTab("changes"),
                  },
                ]
              : []),
            ...(!tempKey && hasPermission("USER_ADMIN")
              ? [
                  {
                    key: "admin",
                    icon: <LockOutlined />,
                    label: "Admin",
                    onClick: () => setTab("admin"),
                  },
                ]
              : []),
            ...(!tempKey &&
            weasisEnabled &&
            study?.study_instance_uid &&
            hasPermission("DICOMWEB_READ")
              ? [
                  {
                    key: "weasis",
                    icon: <DesktopOutlined />,
                    label: "Weasis",
                    onClick: () => {
                      if (study?.study_instance_uid) {
                        openInWeasis(study.study_instance_uid);
                      }
                    },
                  },
                ]
              : []),
            // R-12: Multi-study compare toggle (visible when a study is loaded).
            ...(!tempKey && study?.study_instance_uid
              ? [
                  {
                    key: "compare",
                    icon: <SwapOutlined />,
                    label: compareMode ? "Exit Compare" : "Compare",
                    onClick: () => setCompareMode(!compareMode),
                  },
                ]
              : []),
            ...(!tempKey && !isAdminScoped
              ? [
                  {
                    key: "measurements-toggle",
                    onClick: () => setPanelOpen(!panelOpen),
                    style: {
                      marginLeft: "auto",
                      borderLeft: "1px solid var(--border-color)",
                    },
                    label: (
                      <>
                        <Tooltip title="Toggle measurements panel">
                          <Badge count={measurements.length} size="small" offset={[2, -4]}>
                            <DashboardOutlined />
                          </Badge>
                        </Tooltip>
                        Measures
                      </>
                    ),
                  },
                ]
              : []),
          ]}
        />
        {/* R-12: Compare mode controls — layout toggle + prior study picker. */}
        {compareMode && study?.study_instance_uid && (
          <div
            style={{
              display: "flex",
              gap: 8,
              padding: "4px 16px",
              background: "var(--viewer-bg)",
              borderBottom: "1px solid var(--border-color)",
            }}
          >
            <Radio.Group
              size="small"
              value={compareLayout}
              onChange={(e) => setCompareLayout(e.target.value)}
            >
              <Radio.Button value="2x1">2×1</Radio.Button>
              <Radio.Button value="2x2">2×2</Radio.Button>
            </Radio.Group>
          </div>
        )}
        {data && data.patient && ["image"].includes(tab) && (
          <Breadcrumb
            style={{
              background: "var(--bg-surface)",
              padding: "5px",
              borderRadius: "var(--radius-sm)",
            }}
            items={[
              {
                title: isAdminScoped ? (
                  isMobile ? (
                    data.patient.name
                  ) : (
                    `${data.patient.name} (${data.patient.patient_id})`
                  )
                ) : (
                  <Link to={`/patients/${data.patient_id}`}>
                    {isMobile
                      ? data.patient.name
                      : `${data.patient.name} (${data.patient.patient_id})`}
                  </Link>
                ),
              },
              {
                title: isMobile
                  ? `S:${study?.study_id ?? ""}`
                  : `Study ${study?.study_id ?? ""} ${wrap(study?.description ?? "")}`,
                menu: { items: studiesDrop(data.patient.studies) },
              },
              {
                title: isMobile
                  ? `Ser:${series?.number ?? ""}`
                  : `Series ${series?.number ?? ""} ${wrap(series?.description ?? "")}`,
                menu: { items: seriesDrop(study?.series) },
              },
              {
                title: isMobile ? data.name : `File ${data.name}`,
                menu: { items: filesDrop(series?.files) },
              },
            ]}
          />
        )}
        <div style={{ display: "flex", position: "relative" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
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
              {compareMode ? (
                <StudyCompare
                  images={[
                    { label: "Current", imageUrl: image },
                    ...(priorStudyUid ? [{ label: "Prior", imageUrl: priorStudyUid }] : []),
                  ]}
                  layout={compareLayout}
                  onClose={() => setCompareMode(false)}
                />
              ) : (
                <CornerstoneElement
                  file={data}
                  files={series?.files || null}
                  changeFile={(v: number) => {
                    const target = series?.files?.[v];
                    if (target) navigate(`/files/${target.id}`);
                  }}
                  image={image}
                  progressive={true}
                  visible={tab === "image"}
                  onRequestHelp={() => setShowShortcuts(true)}
                  onAnnotationsChange={handleAnnotationsChange}
                  focusAnnotationUID={focusAnnotationUID}
                  isMobile={isMobile}
                  enableReadingPresets={!isAdminScoped && hasPermission("REPORT_READ")}
                />
              )}
            </Suspense>
          </div>
          {!isAdminScoped && (
            <MeasurementPanel
              measurements={measurements}
              onFocusAnnotation={handleFocusAnnotation}
              collapsed={!panelOpen}
              onToggle={() => setPanelOpen(false)}
              visible={tab === "image"}
            />
          )}
        </div>
        <KeyValueTable
          style={tab !== "data" ? { display: "none" } : {}}
          rowKey={(record: { key: string }) => record.key}
          pagination={{ pageSize: 20 }}
          file={data}
          loading={loading}
        />
        {tab === "changes" && <Changes file={data}></Changes>}
        {tab === "share" && <Share file={data}></Share>}
        {tab === "admin" && hasPermission("USER_ADMIN") && <Management file={data}></Management>}
        <KeyboardShortcuts open={showShortcuts} onClose={() => setShowShortcuts(false)} />
      </PageState>
    </Content>
  );
}

export default withSidebar(Detail);
