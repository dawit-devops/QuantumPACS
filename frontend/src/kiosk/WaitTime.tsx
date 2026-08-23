import React, { useEffect, useState } from "react";
import { Typography, Spin } from "antd";
import { getQueuePosition } from "../api/checkin";

const { Title, Text } = Typography;

interface WaitTimeProps {
  token: string;
}

// K-05: after check-in, display the patient's queue position and estimated
// wait time. Polls every 60s so the display stays current (spec §2.13 K-05).
function WaitTime({ token }: WaitTimeProps) {
  const [position, setPosition] = useState<number | null>(null);
  const [eta, setEta] = useState<number | null>(null);
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    let alive = true;
    const poll = () => {
      getQueuePosition(token)
        .then((res) => {
          if (!alive) return;
          setPosition(res.position);
          setEta(res.eta_minutes);
        })
        .catch(() => {
          if (!alive) return;
        });
    };
    poll();
    const interval = setInterval(poll, 60_000);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, [token]);

  if (position === null) {
    return (
      <div className="kiosk-center">
        <Spin size="large" />
        <Text type="secondary" style={{ marginTop: 16 }}>
          Checking your position in the queue...
        </Text>
      </div>
    );
  }

  return (
    <div className="kiosk-center">
      <div className="kiosk-card kiosk-wait">
        <Title level={3} className="kiosk-title">
          You're checked in!
        </Title>
        <div className="kiosk-wait-number">{position}</div>
        <div className="kiosk-wait-label">
          {position === 1
            ? "You're next in line"
            : `Your position in the queue`}
        </div>
        {eta !== null && (
          <div style={{ marginTop: 16 }}>
            <Text type="secondary" style={{ fontSize: 18 }}>
              Estimated wait: ~{eta} minutes
            </Text>
          </div>
        )}
        <Text
          type="secondary"
          style={{ display: "block", marginTop: 24, fontSize: 14 }}
        >
          Please have a seat — we'll call you when it's time.
        </Text>
      </div>
    </div>
  );
}

export default WaitTime;