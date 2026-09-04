import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { App as AntdApp } from "antd";
import { ThemeProvider } from "../common/ThemeProvider";
import TechnologistWorklist from "../technologist/TechnologistWorklist";

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock("../helpers", () => ({
  request: mockRequest,
  isAdmin: () => true,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
  useTenantRefetch: () => {},
  useVisibilityGatedInterval: () => {},
}));

vi.mock("../common/base", () => ({
  default: (Comp: React.ComponentType<any>) => Comp,
}));

vi.mock("../common/base", () => ({
  default: (Comp: React.ComponentType<any>) => Comp,
}));

let mockUser: { id: string | null; permissions: string[] } = {
  id: null,
  permissions: [],
};

vi.mock("../auth/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../auth/AuthContext")>();
  return {
    ...actual,
    useAuth: () => ({
      user: mockUser.id
        ? { id: mockUser.id, permissions: mockUser.permissions, admin: false, role: "technologist" }
        : null,
      hasPermission: (p: string) =>
        mockUser.permissions.includes(p) || mockUser.permissions.length === 0,
      isAuthenticated: mockUser.id != null,
      signIn: () => {},
      signOut: () => {},
      activeTenant: null,
      setActiveTenant: () => {},
    }),
  };
});

function seedTechSession(userId = "42") {
  mockUser = {
    id: userId,
    permissions: ["EXAM_READ", "EXAM_WRITE"],
  };
}

function renderWorklist() {
  return render(
    <AntdApp>
      <ThemeProvider>
        <MemoryRouter initialEntries={["/exams"]}>
          <TechnologistWorklist />
        </MemoryRouter>
      </ThemeProvider>
    </AntdApp>,
  );
}

const mockExams = [
  {
    id: "e1",
    patient_id: "P001",
    patient_name: "John Doe",
    accession_number: "ACC-001",
    modality: "CT",
    protocol_name: "CT Head (Routine)",
    status: "in_progress",
    priority: "stat",
  },
  {
    id: "e2",
    patient_id: "P002",
    patient_name: "Jane Smith",
    accession_number: "ACC-002",
    modality: "MR",
    protocol_name: "MRI Brain (Routine)",
    status: "ready",
    priority: "routine",
  },
  {
    id: "e3",
    patient_id: "P003",
    patient_name: "Alex Brown",
    accession_number: "ACC-003",
    modality: "CT",
    protocol_name: "CT Chest (Routine)",
    status: "completed",
    priority: "urgent",
  },
];

describe("TechnologistWorklist", () => {
  beforeEach(() => {
    localStorage.clear();
    mockRequest.mockReset();
    // Default: no session (user null) — matches the legacy test baseline.
    mockUser = { id: null, permissions: [] };
  });

  it("renders the assigned exams with priority, modality, and status", async () => {
    mockRequest.mockResolvedValue({ data: mockExams });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
    expect(screen.getByText("Alex Brown")).toBeInTheDocument();
    expect(screen.getByText("STAT")).toBeInTheDocument();
    expect(screen.getByText("CT Head (Routine)")).toBeInTheDocument();
  });

  it("fetches exams with the selected status chip", async () => {
    mockRequest.mockResolvedValue({ data: mockExams });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    // The status chips replace the old Select: click the Completed chip.
    fireEvent.click(screen.getByRole("button", { name: /Completed/ }));

    await waitFor(() => {
      const lastCall =
        mockRequest.mock.calls[mockRequest.mock.calls.length - 1];
      expect(lastCall[0]).toBe("exams");
      expect(lastCall[1].query.status).toBe("completed");
    });
  });

  it("shows the completed-history banner when filtering completed exams", async () => {
    mockRequest.mockResolvedValue({ data: mockExams });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Completed/ }));

    await waitFor(() => {
      expect(
        screen.getByText(/handed off to the radiologist worklist/),
      ).toBeInTheDocument();
    });
  });

  it("shows an empty state when no exams are assigned", async () => {
    mockRequest.mockResolvedValue({ data: [] });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText(/No exams assigned/i)).toBeInTheDocument();
    });
  });

  it("restores the persisted status filter from sessionStorage", async () => {
    sessionStorage.setItem("tech-wl-status", "completed");
    mockRequest.mockResolvedValue({ data: mockExams });
    renderWorklist();

    await waitFor(() => {
      const call = mockRequest.mock.calls.find((c: any) => c[0] === "exams");
      expect(call?.[1]?.query?.status).toBe("completed");
    });
    sessionStorage.removeItem("tech-wl-status");
  });

  it("shows an error alert when the fetch fails", async () => {
    mockRequest.mockRejectedValue(new Error("Network down"));
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("Failed to load worklist")).toBeInTheDocument();
    });
  });

  it("announces and highlights newly assigned exams on refresh", async () => {
    // First poll returns a single exam (the baseline — no announcement).
    let rows: any[] = [{ ...mockExams[0] }];
    mockRequest.mockImplementation(() => Promise.resolve({ data: rows }));
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.queryByText(/^(Exam|Exams) /)).not.toBeInTheDocument();

    // A second exam arrives on the next refresh.
    rows = [mockExams[0], mockExams[1]];
    fireEvent.click(screen.getByRole("button", { name: /Refresh/i }));

    await waitFor(() => {
      expect(screen.getByText("Jane Smith")).toBeInTheDocument();
    });
    // aria-live announces the accession (spec §3-7) and the new row carries
    // the highlight class.
    expect(screen.getByText(/Exam ACC-002 assigned/i)).toBeInTheDocument();
    const row = screen.getByText("Jane Smith").closest("tr");
    expect(row!.className).toContain("tech-wl-row-new");
  });

  it("does not announce existing exams when a filter changes", async () => {
    // Same rows under a new status tab are the new baseline, not arrivals.
    mockRequest.mockResolvedValue({ data: [{ ...mockExams[0] }] });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Ready/i }));

    // The re-fetch under the new filter settles without an announcement.
    await waitFor(() => {
      expect(
        mockRequest.mock.calls.some(
          (c: any[]) => c[1]?.query?.status === "ready",
        ),
      ).toBe(true);
    });
    expect(screen.queryByText(/^(Exam|Exams) /)).not.toBeInTheDocument();
  });

  it("announces the first arrival after an empty worklist", async () => {
    // The first poll returns nothing; the baseline seeds empty. The next
    // poll finds an assignment — that IS an arrival and must be announced.
    let rows: any[] = [];
    mockRequest.mockImplementation(() => Promise.resolve({ data: rows }));
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText(/No exams assigned/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/^(Exam|Exams) /)).not.toBeInTheDocument();

    rows = [{ ...mockExams[0] }];
    fireEvent.click(screen.getByRole("button", { name: /Refresh/i }));

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByText(/Exam ACC-001 assigned/i)).toBeInTheDocument();
    const row = screen.getByText("John Doe").closest("tr");
    expect(row!.className).toContain("tech-wl-row-new");
  });

  it("shows elapsed time since handoff for active exams", async () => {
    const withTimes = [
      {
        ...mockExams[0],
        created_at: new Date(Date.now() - 45 * 60000).toISOString(),
      },
    ];
    mockRequest.mockResolvedValue({ data: withTimes });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("45m")).toBeInTheDocument();
    });
  });

  it("releases an owned exam back to the pool", async () => {
    // T-02: the current user sees a Release action on their owned exams.
    seedTechSession("42");
    const owned = [
      { ...mockExams[0], assigned_technologist: "42" },
      { ...mockExams[1], assigned_technologist: "" },
    ];
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams") return Promise.resolve({ data: owned });
      return Promise.resolve({ data: {} });
    });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    const releaseBtn = screen.getByRole("button", { name: /release exam/i });
    expect(releaseBtn).toBeInTheDocument();
    // The unassigned row shows Claim, not Release.
    expect(
      screen.getByRole("button", { name: /claim exam/i }),
    ).toBeInTheDocument();

    fireEvent.click(releaseBtn);
    await waitFor(() => {
      const call = mockRequest.mock.calls.find((c: any) =>
        (c[0] as string).endsWith("/claim"),
      );
      expect(call).toBeTruthy();
      expect(call![1].data).toEqual({ release: true });
    });
  });

  it("defaults to My Exams and toggles to the unassigned pool", async () => {
    // T-01: the worklist defaults to assigned=mine, and the toggle switches
    // to assigned=pool so the tech can work the shared pool.
    mockRequest.mockImplementation((url: string) => {
      if (url === "exams") return Promise.resolve({ data: mockExams });
      return Promise.resolve({ data: {} });
    });
    renderWorklist();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    // Default fetch is assigned=mine.
    const defaultCall = mockRequest.mock.calls.find(
      (c: any) => c[0] === "exams",
    );
    expect(defaultCall![1].query.assigned).toBe("mine");

    fireEvent.click(screen.getByRole("button", { name: /Unassigned Pool/ }));
    await waitFor(() => {
      const poolCall = mockRequest.mock.calls.find(
        (c: any) => c[0] === "exams" && c[1].query.assigned === "pool",
      );
      expect(poolCall).toBeTruthy();
    });
    // The pool subtitle explains the claim action.
    expect(
      screen.getByText(/Unassigned pool — claim exams to take ownership/),
    ).toBeInTheDocument();
  });
});
