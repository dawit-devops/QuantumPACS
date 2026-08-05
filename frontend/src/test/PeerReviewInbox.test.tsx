import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import PeerReviewInbox from "../radiologist/PeerReviewInbox";

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
}));

// antd's static message API spawns a real React root + auto-dismiss timer;
// after jsdom tears down, the pending scheduler callback throws
// "window is not defined". Stub it like QAReviewForm.test.tsx does.
vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
      warning: vi.fn(),
    },
  };
});

function renderInbox() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/peer-review"]}>
          <PeerReviewInbox />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const mockReview = {
  id: "rev-1",
  report_id: "rep-1",
  reviewer_id: "50",
  status: "assigned",
  discrepancy_level: "",
  comment: "",
  assigned_at: "2026-08-03T10:00:00Z",
  report: {
    id: "rep-1",
    status: "final",
    findings: "Original findings text",
    impression: "Original impression text",
  },
  exam: {
    id: "e1",
    patient_id: "P001",
    patient_name: "John Doe",
    accession_number: "ACC-001",
    modality: "CT",
    priority: "stat",
  },
};

describe("PeerReviewInbox", () => {
  beforeEach(() => {
    localStorage.clear();
    mockRequest.mockReset();
  });

  it("renders my peer-review assignments", async () => {
    mockRequest.mockResolvedValue({ data: [mockReview] });
    renderInbox();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByText("assigned")).toBeInTheDocument();
  });

  it("fetches assignments from peer-reviews", async () => {
    mockRequest.mockResolvedValue({ data: [mockReview] });
    renderInbox();

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith("peer-reviews");
    });
  });

  it("opens a review and shows the original report", async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === "peer-reviews") {
        return Promise.resolve({ data: [mockReview] });
      }
      if (url === "peer-reviews/rev-1") {
        return Promise.resolve({ data: mockReview });
      }
      return Promise.resolve({ data: {} });
    });
    renderInbox();

    await waitFor(() => {
      expect(screen.getByText("Review")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Review"));

    await waitFor(() => {
      expect(screen.getByText("Original Findings")).toBeInTheDocument();
    });
    expect(screen.getByText("Original impression text")).toBeInTheDocument();
  });

  it("submits a discrepancy-level outcome", async () => {
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url === "peer-reviews") {
        return Promise.resolve({ data: [mockReview] });
      }
      if (url === "peer-reviews/rev-1") {
        return Promise.resolve({ data: mockReview });
      }
      if (url === "peer-reviews/rev-1/submit") {
        return Promise.resolve({
          data: {
            ...mockReview,
            status: "completed",
            discrepancy_level: opts.data.discrepancy_level,
            comment: opts.data.comment,
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
    renderInbox();

    await waitFor(() => {
      expect(screen.getByText("Review")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Review"));

    await waitFor(() => {
      expect(screen.getByText("Submit Review Outcome")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Submit Review Outcome"));

    await waitFor(() => {
      expect(screen.getByText("Discrepancy level")).toBeInTheDocument();
    });

    const combobox = screen.getAllByRole("combobox")[0];
    fireEvent.mouseDown(combobox);
    fireEvent.click(await screen.findByTitle("minor"));

    fireEvent.change(screen.getByPlaceholderText(/Feedback/), {
      target: { value: "Agree with findings." },
    });

    const dialog = screen
      .getAllByRole("dialog")
      .find((d) =>
        within(d as HTMLElement).queryByText("Discrepancy level"),
      ) as HTMLElement;
    fireEvent.click(within(dialog).getByRole("button", { name: /^submit$/i }));

    await waitFor(() => {
      const submitCall = mockRequest.mock.calls.find(
        (c: any) => c[0] === "peer-reviews/rev-1/submit",
      ) as any[] | undefined;
      expect(submitCall).toBeDefined();
      expect(submitCall![1].data.discrepancy_level).toBe("minor");
    });
  });

  it("shows an empty state when no reviews are assigned", async () => {
    mockRequest.mockResolvedValue({ data: [] });
    renderInbox();

    await waitFor(() => {
      expect(
        screen.getByText(/No peer reviews assigned to you yet/i),
      ).toBeInTheDocument();
    });
  });

  it("shows an error alert when the fetch fails", async () => {
    mockRequest.mockRejectedValue(new Error("Network down"));
    renderInbox();

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load peer reviews"),
      ).toBeInTheDocument();
    });
  });
});
