import React, { useEffect, useState } from "react";
import { Button, Result, Spin, Typography } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import { confirmCheckIn, getCheckIn, CheckInSummary } from "../api/checkin";
import "./CheckIn.css";

const { Title, Text } = Typography;

type Phase =
  | "loading"
  | "ready"
  | "confirming"
  | "done"
  | "error";

/**
 * RIS-REG-04: kiosk self-check-in. Scans a QR that lands on
 * /checkin?token=...; the token embeds tenant + appointment and
 * expires. Minimal PHI is shown (name + time only).
 */
const CheckIn: React.FC = () => {
  const [phase, setPhase] = useState<Phase>("loading");
  const [summary, setSummary] = useState<CheckInSummary | null>(null);
  const [error, setError] = useState("");

  const token = new URLSearchParams(window.location.search).get("token");

  useEffect(() => {
    if (!token) {
      setError("No check-in token in link.");
      setPhase("error");
      return;
    }
    let alive = true;
    getCheckIn(token)
      .then((s) => {
        if (!alive) return;
        setSummary(s);
        setPhase("ready");
      })
      .catch((e) => {
        if (!alive) return;
        setError(e?.message || "This check-in link is invalid or expired.");
        setPhase("error");
      });
    return () => {
      alive = false;
    };
  }, [token]);

  const onConfirm = async () => {
    if (!token) return;
    setPhase("confirming");
    try {
      await confirmCheckIn(token);
      setPhase("done");
    } catch (e: any) {
      setError(
        e?.status === 409
          ? "You are already checked in."
          : e?.message || "Check-in failed — please see the front desk.",
      );
      setPhase("error");
    }
  };

  if (phase === "loading") {
    return (
      <div className="kiosk-center" data-testid="checkin-loading">
        <Spin size="large" />
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="kiosk-center">
        <Result
          status="error"
          icon={<CloseCircleOutlined />}
          title="Cannot check in"
          subTitle={error}
        />
      </div>
    );
  }

  if (phase === "done") {
    return (
      <div className="kiosk-center">
        <Result
          status="success"
          icon={<CheckCircleOutlined />}
          title="You're checked in"
          subTitle="Please have a seat — we'll call you when it's time."
        />
      </div>
    );
  }

  return (
    <div className="kiosk-center" data-testid="checkin-summary">
      <Title level={3}>Welcome{summary?.patient_name ? `, ${summary.patient_name}` : ""}</Title>
      <Text type="secondary" data-testid="checkin-status">
        Status: {summary?.status}
      </Text>
      <Button
        type="primary"
        size="large"
        style={{ marginTop: 24 }}
        loading={phase === "confirming"}
        onClick={onConfirm}
      >
        I'm here — check me in
      </Button>
    </div>
  );
};

export default CheckIn;
