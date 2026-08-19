import {
  SearchOutlined,
  EyeOutlined,
  ShareAltOutlined,
  CloseOutlined,
  RightOutlined,
  LeftOutlined,
} from "@ant-design/icons";
import { Button, Typography, Space } from "antd";
import React, { useState, useEffect } from "react";

import { useAuth } from "../auth/AuthContext";

const { Text, Title } = Typography;

const TOUR_DONE_KEY = "quantumpacs-tour-done";

const STEPS = [
  {
    title: "Search Studies",
    icon: <SearchOutlined style={{ fontSize: 28, color: "var(--color-primary)" }} />,
    description:
      "Find studies by patient name, ID, or accession number. Use Advanced Search for DICOM tag filtering.",
    targetHint: "Try typing a patient name in the search bar above.",
  },
  {
    title: "View & Diagnose",
    icon: <EyeOutlined style={{ fontSize: 28, color: "var(--color-primary)" }} />,
    description:
      "Interact with images using your mouse or keyboard. Press ? for keyboard shortcuts, or use the measurement tools.",
    targetHint: "Click any study in the list to open the viewer.",
  },
  {
    title: "Share Securely",
    icon: <ShareAltOutlined style={{ fontSize: 28, color: "var(--color-primary)" }} />,
    description:
      "Share studies securely with referring physicians via expiring links. Control access with granular permissions.",
    targetHint: "Open a study and click the Share tab to generate a link.",
  },
];

interface OnboardingTourProps {
  onComplete: () => void;
}

export function OnboardingTour({ onComplete }: OnboardingTourProps) {
  const { isAuthenticated } = useAuth();
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isAuthenticated && !localStorage.getItem(TOUR_DONE_KEY)) {
      setVisible(true);
    }
  }, [isAuthenticated]);

  const dismiss = () => {
    setVisible(false);
    localStorage.setItem(TOUR_DONE_KEY, "true");
    onComplete();
  };

  const next = () => {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      dismiss();
    }
  };

  const prev = () => {
    if (step > 0) setStep(step - 1);
  };

  if (!visible) return null;

  const current = STEPS[step];

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          background: "var(--bg-surface)",
          borderRadius: "var(--radius-xl)",
          boxShadow: "var(--shadow-modal)",
          padding: "32px 40px",
          maxWidth: 420,
          width: "90%",
          pointerEvents: "auto",
          animation: "scale-in var(--duration-normal) var(--easing-enter)",
          border: "1px solid var(--border-color)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: 20,
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "var(--radius-lg)",
              background: "var(--color-info-bg)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {current.icon}
          </div>
          <Button
            type="text"
            icon={<CloseOutlined />}
            onClick={dismiss}
            aria-label="Dismiss tour"
            style={{
              color: "var(--text-muted)",
              marginTop: -8,
              marginRight: -8,
            }}
          />
        </div>

        <Title level={4} style={{ margin: 0, fontSize: 18, color: "var(--text-primary)" }}>
          {current.title}
        </Title>

        <Text
          style={{
            display: "block",
            marginTop: 12,
            lineHeight: 1.6,
            fontSize: 14,
            color: "var(--text-secondary)",
          }}
        >
          {current.description}
        </Text>

        <div
          style={{
            marginTop: 16,
            padding: "10px 14px",
            background: "var(--bg-muted)",
            borderRadius: "var(--radius-md)",
            fontSize: 13,
            color: "var(--text-secondary)",
            borderLeft: "3px solid var(--color-primary)",
          }}
        >
          💡 {current.targetHint}
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 24,
          }}
        >
          <Space>
            {STEPS.map((_, i) => (
              <div
                key={i}
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: i === step ? "var(--color-primary)" : "var(--border-color)",
                  transition: "background var(--duration-fast) var(--easing-standard)",
                }}
              />
            ))}
          </Space>
          <Space>
            <Button
              size="small"
              type="text"
              onClick={dismiss}
              style={{ color: "var(--text-muted)" }}
            >
              Skip
            </Button>
            {step > 0 && (
              <Button size="small" icon={<LeftOutlined />} onClick={prev}>
                Back
              </Button>
            )}
            <Button type="primary" size="small" onClick={next}>
              {step < STEPS.length - 1 ? (
                <>
                  Next <RightOutlined />
                </>
              ) : (
                "Done"
              )}
            </Button>
          </Space>
        </div>

        <Text
          style={{
            display: "block",
            textAlign: "center",
            marginTop: 12,
            fontSize: 11,
            color: "var(--text-muted)",
          }}
        >
          Step {step + 1} of {STEPS.length}
        </Text>
      </div>
    </div>
  );
}
