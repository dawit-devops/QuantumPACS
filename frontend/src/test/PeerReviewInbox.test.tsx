import React from "react";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import { App } from "antd";
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
    <App>
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter initialEntries={["/peer-review"]}>
            <PeerReviewInbox />
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    </App>
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
    // A radiologist: view assignments + submit outcomes (PEER_REVIEW_WRITE).
    // The read-only variant seeds its own session below.
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "radiologist");
    localStorage.setItem("permissions", JSON.stringify(["PEER_REVIEW_READ", "PEER_REVIEW_WRITE"]));
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
    const inProgressReview = { ...mockReview, status: "in_progress" };
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url === "peer-reviews") {
        return Promise.resolve({ data: [inProgressReview] });
      }
      if (url === "peer-reviews/rev-1") {
        return Promise.resolve({ data: inProgressReview });
      }
      if (url === "peer-reviews/rev-1/submit") {
        return Promise.resolve({
          data: {
            ...inProgressReview,
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
      .find((d) => within(d as HTMLElement).queryByText("Discrepancy level")) as HTMLElement;
    fireEvent.click(within(dialog).getByRole("button", { name: /^submit$/i }));

    await waitFor(() => {
      const submitCall = mockRequest.mock.calls.find(
        (c: any) => c[0] === "peer-reviews/rev-1/submit"
      ) as any[] | undefined;
      expect(submitCall).toBeDefined();
      expect(submitCall![1].data.discrepancy_level).toBe("minor");
    });
  });

  it("shows a read-only review for a PEER_REVIEW_READ-only user", async () => {
    // A reviewer without PEER_REVIEW_WRITE views the report but cannot close
    // the review — the submit affordance is replaced by an info notice.
    const inProgressReview = { ...mockReview, status: "in_progress" };
    localStorage.setItem("permissions", JSON.stringify(["PEER_REVIEW_READ"]));
    mockRequest.mockImplementation((url: string) => {
      if (url === "peer-reviews") {
        return Promise.resolve({ data: [inProgressReview] });
      }
      if (url === "peer-reviews/rev-1") {
        return Promise.resolve({ data: inProgressReview });
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
    expect(
      screen.queryByRole("button", { name: /submit review outcome/i })
    ).not.toBeInTheDocument();
    expect(screen.getByText(/requires the PEER_REVIEW_WRITE permission/i)).toBeInTheDocument();
  });

  it("shows an empty state when no reviews are assigned", async () => {
    mockRequest.mockResolvedValue({ data: [] });
    renderInbox();

    await waitFor(() => {
      expect(screen.getByText(/No peer reviews assigned to you yet/i)).toBeInTheDocument();
    });
  });

  it("shows an error alert when the fetch fails", async () => {
    mockRequest.mockRejectedValue(new Error("Network down"));
    renderInbox();

    await waitFor(() => {
      expect(screen.getByText("Failed to load peer reviews")).toBeInTheDocument();
    });
  });

  it("accepts a review, moving it to in-progress", async () => {
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url === "peer-reviews") {
        return Promise.resolve({ data: [mockReview] });
      }
      if (url === "peer-reviews/rev-1") {
        return Promise.resolve({ data: mockReview });
      }
      if (url === "peer-reviews/rev-1/accept") {
        return Promise.resolve({
          data: { ...mockReview, status: "in_progress" },
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
      expect(screen.getByText("Start Review")).toBeInTheDocument();
    });
    // Popconfirm: confirm via its OK button (exact "Start")
    fireEvent.click(screen.getByText("Start Review"));
    fireEvent.click(await screen.findByRole("button", { name: /^start$/i }));

    await waitFor(() => {
      const acceptCall = mockRequest.mock.calls.find(
        (c: any) => c[0] === "peer-reviews/rev-1/accept"
      ) as any[] | undefined;
      expect(acceptCall).toBeDefined();
      expect(acceptCall![1].method).toBe("POST");
    });
    await waitFor(() => {
      expect(screen.queryByText("Start Review")).not.toBeInTheDocument();
      expect(screen.getByText("Submit Review Outcome")).toBeInTheDocument();
    });
  });

  it("declines a review with a reason", async () => {
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url === "peer-reviews") {
        return Promise.resolve({ data: [mockReview] });
      }
      if (url === "peer-reviews/rev-1") {
        return Promise.resolve({ data: mockReview });
      }
      if (url === "peer-reviews/rev-1/decline") {
        return Promise.resolve({
          data: {
            ...mockReview,
            status: "rejected",
            declined_reason: opts.data.reason,
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
      expect(screen.getByText("Decline")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Decline"));

    await waitFor(() => {
      expect(screen.getByText("Decline Peer Review")).toBeInTheDocument();
    });
    const dialog = screen
      .getAllByRole("dialog")
      .find((d) => within(d as HTMLElement).queryByText("Decline Peer Review")) as HTMLElement;
    fireEvent.click(within(dialog).getByRole("button", { name: /^decline$/i }));

    await waitFor(() => {
      const declineCall = mockRequest.mock.calls.find(
        (c: any) => c[0] === "peer-reviews/rev-1/decline"
      ) as any[] | undefined;
      expect(declineCall).toBeDefined();
      expect(declineCall![1].data.reason).toBe("");
    });
  });

  it("shows declined status with reason", async () => {
    const declined = {
      ...mockReview,
      status: "rejected",
      declined_reason: "Out of scope",
    };
    mockRequest.mockImplementation((url: string) => {
      if (url === "peer-reviews") {
        return Promise.resolve({ data: [declined] });
      }
      if (url === "peer-reviews/rev-1") {
        return Promise.resolve({ data: declined });
      }
      return Promise.resolve({ data: {} });
    });
    renderInbox();

    await waitFor(() => {
      expect(screen.getByText("rejected")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Review"));

    await waitFor(() => {
      expect(screen.getByText(/Review declined — Out of scope/)).toBeInTheDocument();
    });
    expect(screen.queryByText("Start Review")).not.toBeInTheDocument();
  });
});
