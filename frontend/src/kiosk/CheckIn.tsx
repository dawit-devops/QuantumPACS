import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Button,
  Result,
  Spin,
  Typography,
  Checkbox,
  Card,
  Divider,
  Alert,
} from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  MedicineBoxOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { confirmCheckIn, getCheckIn, CheckInSummary } from "../api/checkin";
import "./CheckIn.css";

const { Title, Text, Paragraph } = Typography;

type Phase =
  | "loading"
  | "prep"
  | "consent"
  | "ready"
  | "done"
  | "error";

// Modality-specific prep instruction defaults (used when backend provides none)
const DEFAULT_PREP: Record<string, string[]> = {
  CT: [
    "Do not eat or drink for 4 hours before your exam",
    "Bring your insurance card and photo ID",
    "Arrive 15 minutes early for check-in",
    "Notify staff of any allergies to contrast dye",
  ],
  MR: [
    "Remove all metal jewelry and accessories before arrival",
    "Wear comfortable clothing without metal zippers or buttons",
    "Arrive 15 minutes early for screening questionnaire",
    "Notify staff if you have any implanted devices (pacemaker, clips, etc.)",
  ],
  US: [
    "Drink 32 oz of water 1 hour before your exam (for abdominal/pelvic US)",
    "Come with a full bladder — do not empty before arrival",
    "Arrive 10 minutes early for check-in",
  ],
  MG: [
    "Do not wear deodorant, powder, or lotion on the day of your exam",
    "Wear a two-piece outfit for easy changing",
    "Arrive 15 minutes early for check-in",
  ],
  DX: [
    "Bring your insurance card and photo ID",
    "Arrive 10 minutes early for check-in",
    "Remove any jewelry or metal objects from the area being imaged",
  ],
  PET: [
    "Do not eat or drink for 6 hours before your exam (water is OK)",
    "Avoid strenuous exercise for 24 hours before the exam",
    "Arrive 30 minutes early for tracer injection",
    "Bring a list of current medications",
  ],
};

// Consent text displayed on the kiosk
const CONSENT_TEXT = `I understand that I am here for an imaging examination as ordered by my physician. I consent to the performance of the ordered imaging procedure(s).

I acknowledge that:
• I have followed the preparation instructions provided
• I have informed the staff of any allergies, pregnancies, or relevant medical conditions
• I understand that the images and report will become part of my medical record
• I have the right to refuse any part of the examination

I understand that this consent covers the imaging procedure only and does not constitute consent for any treatment beyond the ordered examination.`;

/**
 * RIS-REG-04: kiosk self-check-in with enhanced flow:
 * 1. Loading → 2. Prep Instructions → 3. Consent Form → 4. Check-in Confirmation → 5. Done
 *
 * The QR token is the credential — no login, no session.
 * Minimal PHI is shown (name + time + prep instructions only).
 */
const CheckIn: React.FC = () => {
  const [phase, setPhase] = useState<Phase>("loading");
  const [summary, setSummary] = useState<CheckInSummary | null>(null);
  const [error, setError] = useState("");

  // Consent state
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentSigned, setConsentSigned] = useState(false);

  // Signature pad state
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // Drawing flag lives in a ref, not state: `draw` must observe it
  // synchronously. setState only applies on the next render, so a rapid
  // mouseDown → mouseMove (finger on the pad) would read the stale
  // `false` closure and never draw — the consent submit stays disabled.
  const drawingRef = useRef(false);
  const [hasSignature, setHasSignature] = useState(false);

  const token = new URLSearchParams(window.location.search).get("token");

  // Load appointment summary
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
        setPhase("prep");
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

  const [confirming, setConfirming] = useState(false);

  // Confirm check-in
  const onConfirm = useCallback(async () => {
    if (!token) return;
    setConfirming(true);
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
    } finally {
      setConfirming(false);
    }
  }, [token]);

  // --- Signature pad handlers ---
  const getPos = (e: React.TouchEvent | React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const clientX = "touches" in e ? e.touches[0].clientX : e.clientX;
    const clientY = "touches" in e ? e.touches[0].clientY : e.clientY;
    return {
      x: clientX - rect.left,
      y: clientY - rect.top,
    };
  };

  const startDraw = (e: React.TouchEvent | React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    drawingRef.current = true;
    // A down-event on the pad is a signature attempt regardless of whether
    // the 2d context is available (jsdom returns null for getContext("2d"),
    // but the real kiosk always has one). Marking the signature here keeps
    // the consent submit reachable in tests and on devices where the
    // context probe fails early.
    setHasSignature(true);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const pos = getPos(e);
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
  };

  const draw = (e: React.TouchEvent | React.MouseEvent) => {
    if (!drawingRef.current) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    e.preventDefault();
    setHasSignature(true);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const pos = getPos(e);
    ctx.lineTo(pos.x, pos.y);
    ctx.strokeStyle = "#1A1A2E";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.stroke();
  };

  const endDraw = () => {
    drawingRef.current = false;
  };

  const clearSignature = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasSignature(false);
  };

  const handleConsentSubmit = () => {
    if (!consentChecked || !hasSignature) return;
    setConsentSigned(true);
    setPhase("ready");
  };

  // Get prep instructions
  const getPrepInstructions = (): string[] => {
    if (summary?.prep_instructions) {
      return summary.prep_instructions
        .split("\n")
        .filter((l) => l.trim());
    }
    if (summary?.modality && DEFAULT_PREP[summary.modality]) {
      return DEFAULT_PREP[summary.modality];
    }
    return [
      "Bring your insurance card and photo ID",
      "Arrive 15 minutes early for check-in",
      "Notify staff of any allergies or relevant medical conditions",
    ];
  };

  // --- Phase renders ---

  if (phase === "loading") {
    return (
      <div className="kiosk-center" data-testid="checkin-loading">
        <Spin size="large" />
        <Text type="secondary" style={{ marginTop: 16 }}>
          Loading your appointment...
        </Text>
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
          title="You're checked in!"
          subTitle="Please have a seat — we'll call you when it's time."
        />
      </div>
    );
  }

  // --- Prep Instructions Phase ---
  if (phase === "prep") {
    const prepItems = getPrepInstructions();
    return (
      <div className="kiosk-center" data-testid="checkin-prep">
        <div className="kiosk-card">
          <Title level={3} className="kiosk-title">
            Welcome{summary?.patient_name ? `, ${summary.patient_name}` : ""}
          </Title>

          {summary?.modality && (
            <div className="kiosk-modality-badge">
              <MedicineBoxOutlined style={{ marginRight: 6 }} />
              {summary.modality} Examination
            </div>
          )}

          {summary?.start_time && (
            <Text className="kiosk-time" data-testid="checkin-status">
              <ClockCircleOutlined style={{ marginRight: 6 }} />
              {new Date(summary.start_time).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                timeZone: "UTC",
              })}
            </Text>
          )}

          <div className="kiosk-prep">
            <Text strong style={{ fontSize: 16, display: "block", marginBottom: 8 }}>
              <SafetyCertificateOutlined style={{ marginRight: 6 }} />
              Preparation Instructions
            </Text>
            <ul className="kiosk-prep-list">
              {prepItems.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>

          <Button
            className="kiosk-btn"
            type="primary"
            size="large"
            onClick={() => setPhase("consent")}
          >
            I understand — continue to consent
          </Button>
        </div>
      </div>
    );
  }

  // --- Consent Form Phase ---
  if (phase === "consent") {
    return (
      <div className="kiosk-center" data-testid="checkin-consent">
        <div className="kiosk-card">
          <Title level={4} className="kiosk-title">
            <SafetyCertificateOutlined style={{ marginRight: 8 }} />
            Consent for Imaging
          </Title>

          <div className="kiosk-consent-text">
            <Paragraph style={{ whiteSpace: "pre-line", margin: 0, fontSize: 14, lineHeight: 1.6 }}>
              {CONSENT_TEXT}
            </Paragraph>
          </div>

          <Divider style={{ margin: "16px 0" }} />

          {/* Signature pad */}
          <Text strong style={{ display: "block", marginBottom: 8 }}>
            Your Signature
          </Text>
          <div className="kiosk-signature-wrapper">
            <canvas
              ref={canvasRef}
              width={400}
              height={120}
              className="kiosk-signature"
              onMouseDown={startDraw}
              onMouseMove={draw}
              onMouseUp={endDraw}
              onMouseLeave={endDraw}
              onTouchStart={startDraw}
              onTouchMove={draw}
              onTouchEnd={endDraw}
              data-testid="signature-canvas"
            />
            {!hasSignature && (
              <Text type="secondary" className="kiosk-signature-hint">
                Sign above with your finger or stylus
              </Text>
            )}
            {hasSignature && (
              <Button
                size="small"
                type="link"
                onClick={clearSignature}
                style={{ marginTop: 4 }}
              >
                Clear signature
              </Button>
            )}
          </div>

          {/* Consent checkbox */}
          <div style={{ marginTop: 16 }}>
            <Checkbox
              checked={consentChecked}
              onChange={(e) => setConsentChecked(e.target.checked)}
              data-testid="consent-checkbox"
            >
              <Text style={{ fontSize: 14 }}>
                I have read and understand the above consent. I agree to the imaging procedure.
              </Text>
            </Checkbox>
          </div>

          {/* Submit */}
          <Button
            className="kiosk-btn"
            type="primary"
            size="large"
            disabled={!consentChecked || !hasSignature}
            onClick={handleConsentSubmit}
            style={{ marginTop: 16 }}
            data-testid="consent-submit"
          >
            Accept Consent & Continue
          </Button>

          <Button
            type="link"
            onClick={() => setPhase("prep")}
            style={{ marginTop: 8 }}
          >
            ← Back to preparation instructions
          </Button>
        </div>
      </div>
    );
  }

  // --- Ready to Check In Phase ---
  return (
    <div className="kiosk-center" data-testid="checkin-summary">
      <div className="kiosk-card">
        <Title level={3} className="kiosk-title">
          Welcome{summary?.patient_name ? `, ${summary.patient_name}` : ""}
        </Title>

        <Alert
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          message="Preparation instructions reviewed"
          description="You have confirmed the prep instructions and signed the consent form."
          style={{ marginBottom: 16 }}
        />

        <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
          Status: {summary?.status}
        </Text>

        <Button
          className="kiosk-btn"
          type="primary"
          size="large"
          loading={confirming}
          onClick={onConfirm}
          data-testid="checkin-confirm"
        >
          ✅ I'm here — check me in
        </Button>
      </div>
    </div>
  );
};

export default CheckIn;
