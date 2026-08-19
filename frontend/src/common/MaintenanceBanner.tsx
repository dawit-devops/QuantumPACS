import { Alert } from "antd";
import React, { useEffect, useState } from "react";

import { getAdminStatus } from "../api/admin";

/**
 * Global maintenance-mode banner (super_admin review P1-2). Polls the public
 * status endpoint so every surface — including the login page — shows the
 * pause. Rendered by the app shell and the login page.
 */
function MaintenanceBanner() {
  const [active, setActive] = useState(false);
  const [reason, setReason] = useState("");

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await getAdminStatus();
        if (!cancelled) {
          setActive(res.maintenance.active);
          setReason(res.maintenance.reason ?? "");
        }
      } catch {
        // status is public and best-effort — never block the UI on it
      }
    };
    check();
    const t = setInterval(check, 30000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  if (!active) return null;

  return (
    <Alert
      type="warning"
      banner
      showIcon
      message={
        <span>
          System is in maintenance mode — writes are paused.
          {reason ? ` Reason: ${reason}` : ""}
        </span>
      }
      style={{ borderRadius: 0 }}
    />
  );
}

export default MaintenanceBanner;
