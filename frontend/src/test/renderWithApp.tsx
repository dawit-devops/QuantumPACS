import React from "react";
import { App } from "antd";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";

// antd v6 removed the static-message fallback for App.useApp(), so every
// render of a component that toasts must sit under <App> or the holder
// context is an empty object and message.error() etc. throw.
//
// rerender must re-wrap in <App>: RTL's rerender replaces the root element,
// so passing a bare component would unmount the App wrapper and remount the
// component, losing refs/state (e.g. CornerstoneElement's imageRef guard).
export const renderWithApp = (ui: React.ReactElement) => {
  const result = render(<App>{ui}</App>);
  return {
    ...result,
    rerender: (next: React.ReactElement) => result.rerender(<App>{next}</App>),
  };
};

// (T-L1) Shared wrapper for the standard ThemeProvider + AuthProvider +
// MemoryRouter stack that used to be copy-pasted into every suite.
// initialEntries lets suites start on a specific route (FilesQido, Sidebar).
export const renderWithAuth = (
  ui: React.ReactElement,
  { initialEntries }: { initialEntries?: string[] } = {},
) => {
  return renderWithApp(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
};
