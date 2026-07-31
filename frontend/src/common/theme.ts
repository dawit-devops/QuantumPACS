import type { ThemeConfig } from "antd";
import { theme as antTheme } from "antd";

export const BRAND = {
  primary: "#0891B2",
  secondary: "#22D3EE",
  accent: "#059669",
  success: "#10B981",
  warning: "#F59E0B",
  error: "#DC2626",
  info: "#0891B2",
  bg: "#F8FAFC",
  bgDark: "#0F172A",
  text: "#1E293B",
  textDark: "#F1F5F9",
  textLight: "#94A3B8",
} as const;

export const lightTheme: ThemeConfig = {
  algorithm: antTheme.defaultAlgorithm,
  token: {
    colorPrimary: BRAND.primary,
    colorInfo: BRAND.info,
    colorSuccess: BRAND.success,
    colorWarning: BRAND.warning,
    colorError: BRAND.error,
    colorBgLayout: BRAND.bg,
    colorText: BRAND.text,
    fontFamily:
      "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans', sans-serif",
    borderRadius: 6,
    wireframe: false,
    colorBorder: "#E2E8F0",
    colorBgContainer: "#FFFFFF",
    colorBgElevated: "#FFFFFF",
  },
  components: {
    Button: {
      primaryColor: "#FFFFFF",
      borderRadius: 6,
    },
    Menu: {
      darkItemBg: BRAND.bgDark,
      darkItemSelectedBg: "rgba(6, 182, 212, 0.2)",
      darkItemColor: "rgba(255,255,255,0.65)",
      darkItemSelectedColor: "#22D3EE",
    },
    Layout: {
      headerBg: "#FFFFFF",
      bodyBg: BRAND.bg,
      siderBg: BRAND.bgDark,
    },
    Card: {
      borderRadius: 8,
      colorBgContainer: "#FFFFFF",
    },
    Table: {
      borderRadius: 8,
      headerBg: "#F8FAFC",
    },
    Modal: {
      contentBg: "#FFFFFF",
      headerBg: "#FFFFFF",
    },
    Dropdown: {
      colorBgElevated: "#FFFFFF",
    },
    Popover: {
      colorBgElevated: "#FFFFFF",
    },
    Tooltip: {
      colorBgSpotlight: "#1E293B",
    },
    Notification: {
      colorBgElevated: "#FFFFFF",
    },
  },
};

export const darkTheme: ThemeConfig = {
  algorithm: antTheme.darkAlgorithm,
  token: {
    colorPrimary: "#22D3EE",
    colorInfo: "#22D3EE",
    colorSuccess: "#34D399",
    colorWarning: "#FBBF24",
    colorError: "#F87171",
    colorBgLayout: "#0F172A",
    colorText: "#F1F5F9",
    colorTextSecondary: "#CBD5E1",
    colorTextTertiary: "#94A3B8",
    fontFamily:
      "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans', sans-serif",
    borderRadius: 6,
    wireframe: false,
    colorBorder: "#334155",
    colorBgContainer: "#1E293B",
    colorBgElevated: "#334155",
    colorBgSpotlight: "#475569",
    colorPrimaryBg: "rgba(6, 182, 212, 0.15)",
    colorPrimaryHover: "#67E8F9",
    colorLink: "#22D3EE",
    colorLinkHover: "#67E8F9",
    colorSuccessBg: "rgba(52, 211, 153, 0.15)",
    colorWarningBg: "rgba(251, 191, 36, 0.15)",
    colorErrorBg: "rgba(248, 113, 113, 0.15)",
    colorInfoBg: "rgba(6, 182, 212, 0.15)",
  },
  components: {
    Button: {
      primaryColor: "#0F172A",
      primaryShadow: "none",
      borderRadius: 6,
      defaultBg: "#334155",
      defaultColor: "#F1F5F9",
      defaultBorderColor: "#475569",
    },
    Menu: {
      darkItemBg: "#0F172A",
      darkItemSelectedBg: "rgba(6, 182, 212, 0.25)",
      darkItemColor: "rgba(255,255,255,0.65)",
      darkItemSelectedColor: "#67E8F9",
      itemBg: "#1E293B",
      itemColor: "#CBD5E1",
      itemHoverBg: "rgba(255,255,255,0.04)",
    },
    Layout: {
      headerBg: "#1E293B",
      bodyBg: "#0F172A",
      siderBg: "#0F172A",
      triggerBg: "#334155",
      triggerColor: "#CBD5E1",
    },
    Card: {
      borderRadius: 8,
      colorBgContainer: "#1E293B",
    },
    Table: {
      borderRadius: 8,
      headerBg: "rgba(255,255,255,0.02)",
      headerColor: "#CBD5E1",
      borderColor: "#334155",
      headerSortActiveBg: "rgba(255,255,255,0.04)",
      headerSortHoverBg: "rgba(255,255,255,0.04)",
      bodySortBg: "rgba(255,255,255,0.02)",
      rowHoverBg: "rgba(255,255,255,0.04)",
    },
    Modal: {
      contentBg: "#1E293B",
      headerBg: "#1E293B",
    },
    Dropdown: {
      colorBgElevated: "#334155",
    },
    Popover: {
      colorBgElevated: "#334155",
    },
    Tooltip: {
      colorBgSpotlight: "#475569",
    },
    Notification: {
      colorBgElevated: "#334155",
    },
    Input: {
      colorBgContainer: "#1E293B",
      colorBorder: "#475569",
      colorText: "#F1F5F9",
      addonBg: "#334155",
    },
    Select: {
      colorBgContainer: "#1E293B",
      colorBorder: "#475569",
      selectorBg: "#1E293B",
    },
    DatePicker: {
      colorBgContainer: "#1E293B",
      colorBorder: "#475569",
    },
    Tag: {
      colorBgContainer: "#1E293B",
    },
    Tabs: {
      colorBgContainer: "#1E293B",
    },
    Breadcrumb: {
      itemColor: "#94A3B8",
      lastItemColor: "#F1F5F9",
      linkColor: "#22D3EE",
      separatorColor: "#475569",
    },
    Switch: {
      colorPrimary: "#22D3EE",
    },
    Pagination: {
      colorBgContainer: "#1E293B",
      colorBorder: "#475569",
    },
    Progress: {
      colorBgContainer: "#334155",
    },
    Skeleton: {
      color: "rgba(255,255,255,0.06)",
      borderRadius: 6,
    },
    Alert: {
      colorBgContainer: "#1E293B",
    },
    Spin: {
      colorPrimary: "#22D3EE",
    },
  },
};
