import type { ThemeConfig } from 'antd';

/**
 * Brand tokens — source of truth.
 * CSS variable equivalents in tokens.css.
 * JSON canonical definition in docs/design-tokens.json.
 */
export const BRAND = {
  primary: '#0077B6',
  secondary: '#6366F1',
  accent: '#06B6D4',
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#6366F1',
  bg: '#F8FAFC',
  bgDark: '#0F172A',
  text: '#1E293B',
  textLight: '#94A3B8',
} as const;

export const theme: ThemeConfig = {
  token: {
    colorPrimary: BRAND.primary,
    colorInfo: BRAND.info,
    colorSuccess: BRAND.success,
    colorWarning: BRAND.warning,
    colorError: BRAND.error,
    colorBgLayout: BRAND.bg,
    colorText: BRAND.text,
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    borderRadius: 6,
    wireframe: false,
  },
  components: {
    Button: {
      primaryColor: '#FFFFFF',
      borderRadius: 6,
    },
    Menu: {
      darkItemBg: BRAND.bgDark,
      darkItemSelectedBg: `${BRAND.secondary}33`,
    },
    Layout: {
      headerBg: '#FFFFFF',
      bodyBg: BRAND.bg,
    },
    Card: {
      borderRadius: 8,
    },
    Table: {
      borderRadius: 8,
    },
  },
};
