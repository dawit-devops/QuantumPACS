import { useDocumentTitle } from "../hooks";
import React, { Suspense, useState, useEffect, useCallback } from "react";
import { Link } from "react-router";
import withRouter from "../withRouter";
import {
  Layout,
  message,
  Menu,
  Breadcrumb,
  Grid,
  Spin,
  Badge,
  Tooltip,
} from "antd";
import {
  EyeOutlined,
  TableOutlined,
  ShareAltOutlined,
  HistoryOutlined,
  LockOutlined,
  DashboardOutlined,
} from "@ant-design/icons";
import { useTheme } from "../common/ThemeProvider";
import { KeyboardShortcuts } from "./KeyboardShortcuts";
import { parseAnnotations } from "./MeasurementPanel";
import MeasurementPanel from "./MeasurementPanel";
import { PageState } from "../common/PageState";
import withSidebar from "../common/base";

const { useBreakpoint } = Grid;
import { getFile } from "../api/files";
import { wadoRsUrl } from "../api/studies";
import { useAuth } from "../auth/AuthContext";
import { API_URL } from "../config";
const CornerstoneElement = React.lazy(() => import("./CornerstoneElement"));
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

function Detail(props: any) {
  useDocumentTitle("QuantumPACS - Detail");
  const imagePath = `wadouri:${API_URL}/files/${props.match.params.id}/data`;
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const { hasPermission } = useAuth();

  let [tab, setTab] = useState("image");
  let [data, setData] = useState<any>({});
  let [loading, setLoading] = useState(false);
  let [error, setError] = useState<string | null>(null);
  let [study, setStudy] = useState<any>(null);
  let [series, setSeries] = useState<any>(null);
  let [image, setImage] = useState(imagePath);
  let [wadoRsImage, setWadoRsImage] = useState<string | null>(null);
  const tempKey = localStorage.getItem("tempKey");
  const [showShortcuts, setShowShortcuts] = useState(false);

  const [rawAnnotations, setRawAnnotations] = useState<any[]>([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const [focusAnnotationUID, setFocusAnnotationUID] = useState<string | null>(
    null,
  );

  const imageUrl = wadoRsImage || image;

  const measurements = parseAnnotations(rawAnnotations, imageUrl);

  const handleAnnotationsChange = useCallback((annotations: any[]) => {
    setRawAnnotations(annotations || []);
  }, []);

  const handleFocusAnnotation = useCallback((annotationUID: string) => {
    setFocusAnnotationUID(annotationUID);
    setTimeout(() => setFocusAnnotationUID(null), 100);
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    let params = props.match.params;

    setImage(`wadouri:${API_URL}/files/${params.id}/data`);

    getFile(params.id)
      .then((data: any) => {
        const meta = data?.meta || {};
        if (
          meta.study_instance_uid &&
          meta.series_instance_uid &&
          meta.sop_instance_uid
        ) {
          setWadoRsImage(
            wadoRsUrl(
              meta.study_instance_uid,
              meta.series_instance_uid,
              meta.sop_instance_uid,
            ),
          );
        }
        // Mount the viewer only once all metadata is in place: the remount
        // hack below used to force a second mount because the viewer could
        // initialize with empty props. CornerstoneElement now mounts
        // after-metadata and its checkReady loop covers engine readiness.
        for (let s of data.patient.studies) {
          if (s.id === data.study_db_id) {
            setStudy(s);
            for (let sr of s.series) {
              if (sr.id === data.series_db_id) {
                setSeries(sr);
              }
            }
          }
        }
        setData(data);
        setLoading(false);
      })
      .catch((e: any) => {
        setLoading(false);
        let msg = "File fail to load";
        if (e.message === "404") {
          msg = "File not found";
        }
        setError(msg);
        message.error(msg);
        if (e.message === "404") {
          props.history.push("/");
        }
      });
    // eslint-disable-next-line
  }, [props.match.params.id]);

  const background = tab === "image" ? "var(--viewer-bg)" : "";

  const changeStudy = (e: any, s: any) => {
    e.preventDefault();
    setStudy(s);
    setSeries(s.series[0]);
  };

  const studiesDrop = (data: any) => {
    if (!data) return [];
    return data.map((d: any) => ({
      key: d.study_id,
      label: (
        <a
          href=""
          onClick={(e: any) => changeStudy(e, d)}
        >{`Study ${d.study_id} ${wrap(d.description)}`}</a>
      ),
    }));
  };

  const changeSeries = (e: any, s: any) => {
    e.preventDefault();
    setSeries(s);
  };

  const seriesDrop = (data: any) => {
    if (!data) return [];
    return data.map((d: any) => ({
      key: d.number,
      label: (
        <a
          href=""
          onClick={(e: any) => changeSeries(e, d)}
        >{`Series ${d.number} ${wrap(d.description)}`}</a>
      ),
    }));
  };

  const filesDrop = (data: any) => {
    if (!data) return [];
    return data.map((d: any) => ({
      key: d.id,
      label: <Link to={`/files/${d.id}`}>{`File ${d.name}`}</Link>,
    }));
  };

  return (
    <Content
      style={{
        alignItems: "center",
        justifyContent: "center",
        background: background,
      }}
    >
      <PageState loading={loading && !data.id} error={error}>
        <Menu
          style={{ paddingLeft: "40px" }}
          defaultSelectedKeys={[tab]}
          mode="horizontal"
        >
          <Menu.Item key="image" onClick={() => setTab("image")}>
            <EyeOutlined />
            Image
          </Menu.Item>
          <Menu.Item key="data" onClick={() => setTab("data")}>
            <TableOutlined />
            Data
          </Menu.Item>
          {!tempKey && (
            <Menu.Item key="share" onClick={() => setTab("share")}>
              <ShareAltOutlined />
              Share
            </Menu.Item>
          )}
          {!tempKey && (
            <Menu.Item key="changes" onClick={() => setTab("changes")}>
              <HistoryOutlined />
              Changes
            </Menu.Item>
          )}
          {!tempKey && hasPermission("USER_ADMIN") && (
            <Menu.Item key="admin" onClick={() => setTab("admin")}>
              <LockOutlined />
              Admin
            </Menu.Item>
          )}
          <Menu.Item
            key="measurements-toggle"
            onClick={() => setPanelOpen(!panelOpen)}
            style={{
              marginLeft: "auto",
              borderLeft: "1px solid var(--border-color)",
            }}
          >
            <Tooltip title="Toggle measurements panel">
              <Badge count={measurements.length} size="small" offset={[2, -4]}>
                <DashboardOutlined />
              </Badge>
            </Tooltip>
            Measures
          </Menu.Item>
        </Menu>
        {data && data.patient && ["image"].includes(tab) && (
          <Breadcrumb
            style={{
              background: "var(--bg-surface)",
              padding: "5px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            <Breadcrumb.Item>
              <Link to={`/patients/${data.patient_id}`}>
                {isMobile
                  ? data.patient.name
                  : `${data.patient.name} (${data.patient.patient_id})`}
              </Link>
            </Breadcrumb.Item>
            <Breadcrumb.Item
              menu={{ items: studiesDrop(data.patient.studies) }}
            >
              {isMobile
                ? `S:${study?.study_id}`
                : `Study ${study?.study_id} ${wrap(study?.description)}`}
            </Breadcrumb.Item>
            <Breadcrumb.Item menu={{ items: seriesDrop(study?.series) }}>
              {isMobile
                ? `Ser:${series?.number}`
                : `Series ${series?.number} ${wrap(series?.description)}`}
            </Breadcrumb.Item>
            <Breadcrumb.Item menu={{ items: filesDrop(series?.files) }}>
              {isMobile ? data.name : `File ${data.name}`}
            </Breadcrumb.Item>
          </Breadcrumb>
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
              <CornerstoneElement
                file={data}
                files={series?.files || null}
                changeFile={(v: number) =>
                  props.history.push(`/files/${series?.files[v].id}`)
                }
                image={image}
                wadoRsImage={wadoRsImage}
                progressive={true}
                visible={tab === "image"}
                onRequestHelp={() => setShowShortcuts(true)}
                onAnnotationsChange={handleAnnotationsChange}
                focusAnnotationUID={focusAnnotationUID}
                isMobile={isMobile}
              />
            </Suspense>
          </div>
          <MeasurementPanel
            measurements={measurements}
            onFocusAnnotation={handleFocusAnnotation}
            collapsed={!panelOpen}
            onToggle={() => setPanelOpen(false)}
            visible={tab === "image"}
          />
        </div>
        <KeyValueTable
          style={tab !== "data" ? { display: "none" } : {}}
          rowKey={(record: any) => record.key}
          pagination={{ pageSize: 20 }}
          file={data}
          loading={loading}
        />
        {tab === "changes" && <Changes file={data}></Changes>}
        {tab === "share" && <Share file={data}></Share>}
        {tab === "admin" && hasPermission("USER_ADMIN") && (
          <Management file={data}></Management>
        )}
        <KeyboardShortcuts
          open={showShortcuts}
          onClose={() => setShowShortcuts(false)}
        />
      </PageState>
    </Content>
  );
}

export default withSidebar(withRouter(Detail));
