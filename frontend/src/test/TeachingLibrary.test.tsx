import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import TeachingLibrary from "../radiologist/TeachingLibrary";

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock("../helpers", () => ({
  request: mockRequest,
  isAdmin: () => false,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

vi.mock("../common/base", () => ({
  default: (Component: React.ComponentType) =>
    function MockedBase() {
      return <Component />;
    },
}));

const mockFiles = {
  data: [
    {
      id: "tf-1",
      title: "Classic CT head",
      modality: "CT",
      body_part: "Head",
      diagnosis: "Subdural hematoma",
      difficulty: "easy",
      teaching_points: ["Always check the midline shift"],
      differential_diagnosis: ["EDH", "SAH"],
      created_at: "2026-08-24T10:00:00Z",
    },
    {
      id: "tf-2",
      title: "Subtle PE",
      modality: "CT",
      body_part: "Chest",
      diagnosis: "Pulmonary embolism",
      difficulty: "hard",
      teaching_points: [],
      differential_diagnosis: [],
      created_at: "2026-08-20T10:00:00Z",
    },
  ],
};

function renderLibrary() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/teaching"]}>
          <TeachingLibrary />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

describe("TeachingLibrary", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "resident");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["REPORT_READ", "REPORT_WRITE"]),
    );
    mockRequest.mockReset();
    mockRequest.mockImplementation((url: string) => {
      if (url === "teaching-files") return Promise.resolve(mockFiles);
      if (url === "teaching-files/tf-1") {
        return Promise.resolve({ data: mockFiles.data[0] });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it("lists curated teaching cases (RES-03)", async () => {
    renderLibrary();

    await waitFor(() => {
      expect(screen.getByText(/Classic CT head/)).toBeInTheDocument();
      expect(screen.getByText(/Subtle PE/)).toBeInTheDocument();
    });
  });

  it("opens a case detail drawer with teaching points", async () => {
    renderLibrary();

    await waitFor(() => {
      expect(screen.getByText(/Classic CT head/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /open classic ct head/i }));
    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith("teaching-files/tf-1");
      expect(screen.getByText(/Always check the midline shift/)).toBeInTheDocument();
    });
  });

  it("passes the difficulty filter through to the API", async () => {
    renderLibrary();

    await waitFor(() => {
      expect(screen.getByText(/Classic CT head/)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Diagnosis"), {
      target: { value: "hematoma" },
    });

    const combos = screen.getAllByRole("combobox");
    fireEvent.mouseDown(combos[combos.length - 1]);
    // "hard" matches both the card tag and the dropdown option — pick the
    // dropdown's option-content node.
    const hardEls = await screen.findAllByText("hard");
    const optEl = hardEls.find((el) =>
      el.className.includes("ant-select-item-option"),
    );
    fireEvent.click(optEl ?? hardEls[hardEls.length - 1]);

    await waitFor(() => {
      const lastCall = mockRequest.mock.calls.find(
        (c: any[]) => String(c[0]).startsWith("teaching-files?"),
      );
      expect(lastCall).toBeDefined();
      expect(String(lastCall![0])).toContain("difficulty=hard");
    });
  });
});
