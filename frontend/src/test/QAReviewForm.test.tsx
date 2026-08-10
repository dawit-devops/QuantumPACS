import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import QAReviewForm from "../qa/QAReviewForm";

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
// "window is not defined". Stub it like Worklist.test.tsx does.
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

function renderReview() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/qa/review/e1"]}>
          <Routes>
            <Route path="/qa/review/:examId" element={<QAReviewForm />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const mockReview = {
  exam: {
    id: "f1",
    patient_id: "P001",
    patient_name: "John Doe",
    accession_number: "ACC-100",
    modality: "CT",
    priority: "stat",
    protocol_name: "CT Head (Routine)",
    assigned_technologist: "tech-1",
    completed_at: "2026-08-03T10:00:00Z",
  },
  protocol: {
    id: "p1",
    name: "CT Head (Routine)",
    sequences: [
      { name: "Axial", required: true },
      { name: "Coronal", required: false },
    ],
  },
  score: null,
};

describe("QAReviewForm", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("userId", "qa-1");
    localStorage.setItem("username", "qa_user");
    localStorage.setItem("admin", "true");
    localStorage.setItem("role", "qa_officer");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["QA_READ", "QA_WRITE", "PROTOCOL_MANAGE"]),
    );
    mockRequest.mockReset();
    mockRequest.mockResolvedValue({ data: mockReview });
  });

  it("loads and renders the exam summary", async () => {
    renderReview();
    expect(await screen.findByText(/QA Review — ACC-100/)).toBeInTheDocument();
    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("CT")).toBeInTheDocument();
  });

  it("renders the sequence checklist from the protocol", async () => {
    renderReview();
    await screen.findByText(/QA Review — ACC-100/);
    expect(screen.getByText("Axial")).toBeInTheDocument();
    expect(screen.getByText(/Coronal.*\(optional\)/)).toBeInTheDocument();
  });

  it("submits a QA score and navigates back to the queue", async () => {
    renderReview();
    await screen.findByText(/QA Review — ACC-100/);
    const submitBtn = screen.getByText("Submit QA score");
    fireEvent.click(submitBtn);
    await waitFor(() => {
      const postCall = mockRequest.mock.calls.find(
        (c: any[]) => c[0] === "qa/reviews" && c[1].method === "POST",
      );
      expect(postCall).toBeTruthy();
      expect(postCall![1].data.exam_id).toBe("e1");
      expect(postCall![1].data.pass_fail).toBe("pass");
    });
  });

  it("pre-fills fields from an existing score", async () => {
    mockRequest.mockResolvedValue({
      data: {
        ...mockReview,
        score: {
          pass_fail: "fail",
          discrepancy_level: "major",
          dose_dlp: 980,
          dose_ctdivol: 55,
          dose_kvp: 120,
          dose_mas: 300,
          sequence_compliance: { Axial: true },
          comments: "Retake required",
        },
      },
    });
    renderReview();
    await waitFor(() => {
      expect(screen.getByText("Update QA score")).toBeInTheDocument();
    });
    expect(screen.getByText(/Already reviewed as "fail"/)).toBeInTheDocument();
  });
});
