import React, { useState, useEffect } from "react";
import { App, Layout, Tabs } from "antd";
import withSidebar from "../common/base";
import {
  listHl7Messages,
  getHl7Message,
  getHl7Metrics,
  getHl7Config,
  updateHl7Config,
  getHl7Status,
} from "../api/hl7";
import { PageState } from "../common/PageState";
import { useAuth } from "../auth/AuthContext";
import { MessagesTab } from "./MessagesTab";
import { AnalyticsTab } from "./AnalyticsTab";
import { ConfigTab } from "./ConfigTab";
import { DetailModal } from "./DetailModal";
import "./Hl7.css";

const { Content } = Layout;

function Hl7Dashboard() {
  const { message } = App.useApp();
  // HL7_READ gates the page; the Configuration tab's Save hits HL7_WRITE.
  const { hasPermission } = useAuth();
  const canWriteConfig = hasPermission("HL7_WRITE");

  // Messages tab
  const [messages, setMessages] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [msgLoading, setMsgLoading] = useState(true);
  const [msgError, setMsgError] = useState<string | null>(null);
  const [msgFilter, setMsgFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [patientFilter, setPatientFilter] = useState("");
  const [facilityFilter, setFacilityFilter] = useState("");
  const [limit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [detailModal, setDetailModal] = useState<any>(null);

  // Analytics tab
  const [metrics, setMetrics] = useState<any>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [period, setPeriod] = useState("24h");

  // Config tab
  const [config, setConfig] = useState<any>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [allowedIpsText, setAllowedIpsText] = useState("");
  const [mllpPort, setMllpPort] = useState(12579);

  const fetchMessages = async () => {
    setMsgLoading(true);
    setMsgError(null);
    try {
      const res = await listHl7Messages({
        limit,
        offset,
        ...(msgFilter ? { message_type: msgFilter } : {}),
        ...(statusFilter ? { parse_status: statusFilter } : {}),
        ...(patientFilter ? { patient_id: patientFilter } : {}),
        ...(facilityFilter ? { sending_facility: facilityFilter } : {}),
      });
      setMessages(res.messages || []);
      setTotal(res.total || 0);
    } catch (e: any) {
      setMsgError(e.message);
    } finally {
      setMsgLoading(false);
    }
  };

  const fetchMetrics = async () => {
    setMetricsLoading(true);
    try {
      const res = await getHl7Metrics(period);
      setMetrics(res);
    } catch {
    } finally {
      setMetricsLoading(false);
    }
  };

  const fetchConfig = async () => {
    setConfigLoading(true);
    try {
      const res = await getHl7Config();
      setConfig(res);
      setConfigError(null);
      setAllowedIpsText((res.allowed_ips || []).join("\n"));
      setMllpPort(res.mllp_port || 12579);
    } catch (e: any) {
      // Surface load failures: with config left null the Save button stays
      // disabled so a failed load can never overwrite the server's real
      // configuration with local defaults.
      setConfig(null);
      setConfigError(e.message);
    } finally {
      setConfigLoading(false);
    }
  };

  const fetchStatus = async () => {
    setStatusLoading(true);
    try {
      const res = await getHl7Status();
      setStatus(res);
    } catch {
    } finally {
      setStatusLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset, msgFilter, statusFilter, patientFilter, facilityFilter]);

  useEffect(() => {
    // (P-M11) Coalesce the three mount-only fetches into one effect so the
    // browser fires them together rather than on three separate effect
    // passes; each still updates its own state independently on failure.
    fetchMetrics();
    fetchConfig();
    fetchStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleViewDetail = async (id: string) => {
    try {
      const res = await getHl7Message(id);
      setDetailModal(res);
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleSaveConfig = async () => {
    if (!config) {
      message.error("Configuration failed to load — reload before saving");
      return;
    }
    setConfigSaving(true);
    try {
      const ips = allowedIpsText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      await updateHl7Config({ mllp_port: mllpPort, allowed_ips: ips });
      message.success("Configuration saved");
      fetchConfig();
      fetchStatus();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setConfigSaving(false);
    }
  };

  return (
    <Content className="hl7-dashboard" style={{ padding: 24 }}>
      <Tabs
        defaultActiveKey="messages"
        items={[
          {
            key: "messages",
            label: "Messages",
            children: (
              <MessagesTab
                messages={messages}
                total={total}
                loading={msgLoading}
                error={msgError}
                msgFilter={msgFilter}
                setMsgFilter={setMsgFilter}
                statusFilter={statusFilter}
                setStatusFilter={setStatusFilter}
                patientFilter={patientFilter}
                setPatientFilter={setPatientFilter}
                facilityFilter={facilityFilter}
                setFacilityFilter={setFacilityFilter}
                limit={limit}
                offset={offset}
                setOffset={setOffset}
                fetchMessages={fetchMessages}
                onViewDetail={handleViewDetail}
              />
            ),
          },
          {
            key: "analytics",
            label: "Analytics",
            children: (
              <AnalyticsTab
                metrics={metrics}
                loading={metricsLoading}
                period={period}
                setPeriod={setPeriod}
                fetchMetrics={fetchMetrics}
              />
            ),
          },
          {
            key: "config",
            label: "Configuration",
            children: (
              <ConfigTab
                config={config}
                configLoading={configLoading}
                configError={configError}
                status={status}
                statusLoading={statusLoading}
                configSaving={configSaving}
                mllpPort={mllpPort}
                setMllpPort={setMllpPort}
                allowedIpsText={allowedIpsText}
                setAllowedIpsText={setAllowedIpsText}
                fetchConfig={fetchConfig}
                fetchStatus={fetchStatus}
                handleSaveConfig={handleSaveConfig}
                canWrite={canWriteConfig}
              />
            ),
          },
        ]}
      />
      <DetailModal detail={detailModal} onClose={() => setDetailModal(null)} />
    </Content>
  );
}

export default withSidebar(Hl7Dashboard);
