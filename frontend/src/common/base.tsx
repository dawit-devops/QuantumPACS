import React from "react";
import { Layout, Grid } from "antd";
import Sidebar from "./Sidebar";
import MobileNav from "./MobileNav";
import { useTheme } from "./ThemeProvider";

const { useBreakpoint } = Grid;

function withSidebar(Comp: React.ComponentType<any>) {
  function wrapper(props: any) {
    const screens = useBreakpoint();
    const isMobile = !screens.lg;
    const tempKey = sessionStorage.getItem("tempKey");
    const { isDark } = useTheme();
    return (
      <Layout
        style={{
          minHeight: "100dvh",
          paddingBottom:
            isMobile && !tempKey
              ? "calc(56px + env(safe-area-inset-bottom, 0px))"
              : 0,
          paddingLeft: "env(safe-area-inset-left, 0px)",
          paddingRight: "env(safe-area-inset-right, 0px)",
          transition:
            "background-color var(--duration-normal) var(--easing-standard)",
        }}
      >
        <a
          href="#main-content"
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
      </Layout>
    );
  }
  return wrapper;
}

export default withSidebar;
