import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button, Result, Spin, Typography, Checkbox, Card, Divider, Alert, Input } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  MedicineBoxOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { confirmCheckIn, getCheckIn, submitConsent, CheckInSummary } from "../api/checkin";
import SignaturePad, { type SignaturePadHandle } from "../common/SignaturePad";
import CoPayPrompt from "./CoPayPrompt";
import WaitTime from "./WaitTime";
import "./CheckIn.css";

const { Title, Text, Paragraph } = Typography;

type Phase = "loading" | "prep" | "consent" | "ready" | "copay" | "done" | "error";

// K-04: default co-pay amount presented at the kiosk (configurable per
// tenant later; today a fixed placeholder derived from the modality).
const COPRAY_AMOUNT = 25.0;

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
  // K-04: the receipt returned by the payment endpoint — shown on the done
  // screen so the patient can note the number or print a copy.
  const [receipt, setReceipt] = useState<{ receipt_number?: string } | null>(null);

  // Consent state
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentSigned, setConsentSigned] = useState(false);

  // Shared signature pad (spec §2.12) — drawing handlers live inside the
  // component; the imperative handle exposes capture()/clear().
  const padRef = useRef<SignaturePadHandle>(null);
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
  const [submittingConsent, setSubmittingConsent] = useState(false);
  const [declineReason, setDeclineReason] = useState("");
  const [declining, setDeclining] = useState(false);

  // Confirm check-in
  const onConfirm = useCallback(async () => {
    if (!token) return;
    setConfirming(true);
    try {
      await confirmCheckIn(token);
      setPhase("copay");
    } catch (e: any) {
      setError(
        e?.status === 409
          ? "You are already checked in."
          : e?.message || "Check-in failed — please see the front desk."
      );
      setPhase("error");
    } finally {
      setConfirming(false);
    }
  }, [token]);

  const captureSignature = (): string => {
    return padRef.current?.capture() || "";
  };

  const handleConsentSubmit = async () => {
    if (!consentChecked || !hasSignature || !token) return;
    setSubmittingConsent(true);
    try {
      const signature_png = captureSignature();
      await submitConsent(token, {
        accepted: true,
        signature_png,
        decline_reason: "",
      });
      setConsentSigned(true);
      setPhase("ready");
    } catch (e: any) {
      setError(e?.message || "Failed to submit consent");
      setPhase("error");
    } finally {
      setSubmittingConsent(false);
    }
  };

  const handleDecline = async () => {
    if (!token || !declineReason.trim()) return;
    setSubmittingConsent(true);
    try {
      await submitConsent(token, {
        accepted: false,
        signature_png: "",
        decline_reason: declineReason.trim(),
      });
      setConsentSigned(true);
      setPhase("ready");
    } catch (e: any) {
      setError(e?.message || "Failed to record decline");
      setPhase("error");
    } finally {
      setSubmittingConsent(false);
    }
  };

  // Get prep instructions
  const getPrepInstructions = (): string[] => {
    if (summary?.prep_instructions) {
      return summary.prep_instructions.split("\n").filter((l) => l.trim());
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
        {token && <WaitTime token={token} />}
        {!token && (
          <Result
            status="success"
            icon={<CheckCircleOutlined />}
            title="You're checked in!"
            subTitle="Please have a seat — we'll call you when it's time."
          />
        )}
        {receipt?.receipt_number && (
          <div className="kiosk-receipt" data-testid="kiosk-receipt">
            <Divider />
            <Text strong>Payment receipt</Text>
            <div className="kiosk-receipt-number">#{receipt.receipt_number}</div>
            <Button onClick={() => window.print()} className="kiosk-copay-skip">
              Print receipt
            </Button>
          </div>
        )}
      </div>
    );
  }

  // --- Co-pay Phase (K-04) ---
  if (phase === "copay" && token) {
    return (
      <CoPayPrompt
        token={token}
        amount={COPRAY_AMOUNT}
        onComplete={(rcpt) => {
          setReceipt(rcpt);
          setPhase("done");
        }}
        onSkip={() => setPhase("done")}
      />
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
            <SignaturePad
              ref={padRef}
              onSignatureChange={setHasSignature}
              width={400}
              height={120}
              hint="Sign above with your finger or stylus"
              clearLabel="Clear signature"
              testId="signature-canvas"
            />
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
            loading={submittingConsent}
            onClick={handleConsentSubmit}
            style={{ marginTop: 16 }}
            data-testid="consent-submit"
          >
            Accept Consent & Continue
          </Button>

          <Divider style={{ margin: "16px 0" }} />

          {/* Decline flow — refusal still allows check-in (K-03) */}
          {!declining ? (
            <Button
              type="link"
              danger
              onClick={() => setDeclining(true)}
              data-testid="decline-consent"
            >
              I decline this consent
            </Button>
          ) : (
            <div className="kiosk-decline">
              <Input.TextArea
                placeholder="Reason for declining (required)"
                value={declineReason}
                onChange={(e) => setDeclineReason(e.target.value)}
                rows={2}
                maxLength={500}
                data-testid="decline-reason"
              />
              <Button
                type="primary"
                danger
                block
                disabled={!declineReason.trim()}
                loading={submittingConsent}
                onClick={handleDecline}
                style={{ marginTop: 8 }}
                data-testid="decline-submit"
              >
                Decline Consent — proceed to check-in
              </Button>
              <Button
                type="link"
                size="small"
                onClick={() => {
                  setDeclining(false);
                  setDeclineReason("");
                }}
                style={{ marginTop: 4 }}
              >
                Back to accept consent
              </Button>
            </div>
          )}

          <Button type="link" onClick={() => setPhase("prep")} style={{ marginTop: 8 }}>
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
