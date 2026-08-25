import { Layout, Grid } from "antd";
import React from "react";
import { useLocation } from "react-router";

import MaintenanceBanner from "./MaintenanceBanner";
import MobileNav from "./MobileNav";
import Sidebar from "./Sidebar";
import { useTheme } from "./ThemeProvider";
import PatientSearchOverlay from "../frontdesk/PatientSearchOverlay";

const { useBreakpoint } = Grid;

function withSidebar(Comp: React.ComponentType<any>) {
  function wrapper(props: any) {
    const screens = useBreakpoint();
    const isMobile = !screens.lg;
    const tempKey = sessionStorage.getItem("tempKey");
    const { isDark } = useTheme();
    const location = useLocation();
    const onFrontDesk = location.pathname.startsWith("/frontdesk");
    // CC-13: the patient quick-search overlay serves every staff persona
    // that works patient-by-patient — coordination (orders, prior auth,
    // reminders) and billing ride the same global mount as front desk.
    const onCoordination =
      ["/orders", "/prior-auth", "/reminders", "/care-plans",
       "/communications", "/teaching"].some((p) =>
        location.pathname.startsWith(p),
      );
    const onBilling = [
      "/billing/queue", "/billing/claims", "/billing/revenue",
      "/billing/denials", "/billing/unbilled",
    ].some((p) => location.pathname.startsWith(p));
    return (
      <Layout
        style={{
          minHeight: "100dvh",
          paddingBottom: isMobile && !tempKey ? "calc(56px + env(safe-area-inset-bottom, 0px))" : 0,
          paddingLeft: "env(safe-area-inset-left, 0px)",
          paddingRight: "env(safe-area-inset-right, 0px)",
          transition: "background-color var(--duration-normal) var(--easing-standard)",
        }}
      >
        <MaintenanceBanner />
        <a
          href="#main-content"
          className="skip-link"
          style={{
            position: "absolute" as const,
            left: "-9999px",
            width: "1px",
            height: "1px",
            overflow: "hidden",
            zIndex: 9999,
          }}
          onFocus={(e) => {
            e.currentTarget.style.left = "8px";
            e.currentTarget.style.top = "8px";
            e.currentTarget.style.width = "auto";
            e.currentTarget.style.height = "auto";
            e.currentTarget.style.padding = "8px 16px";
            e.currentTarget.style.background = "var(--bg-surface)";
            e.currentTarget.style.borderRadius = "4px";
            e.currentTarget.style.fontSize = "14px";
            e.currentTarget.style.fontWeight = "600";
          }}
          onBlur={(e) => {
            e.currentTarget.style.left = "-9999px";
            e.currentTarget.style.width = "1px";
            e.currentTarget.style.height = "1px";
            e.currentTarget.style.padding = "0";
          }}
        >
          Skip to content
        </a>
        {!tempKey && <Sidebar {...props} isDark={isDark} />}
        <div
          className="page-content"
          id="main-content"
          style={{
            flex: 1,
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Comp {...props} />
        </div>
        {isMobile && !tempKey && <MobileNav />}
        {(onFrontDesk || onCoordination || onBilling) && (
          <PatientSearchOverlay />
        )}
      </Layout>
    );
  }
  return wrapper;
}

export default withSidebar;
