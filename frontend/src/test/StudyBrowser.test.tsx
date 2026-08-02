import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import StudyBrowser from "../dicomweb/StudyBrowser";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function mockDicomJsonResponse(data: any) {
  return { ok: true, json: () => Promise.resolve(data) };
}

describe("StudyBrowser", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("access_token", "test");
  });

  it("renders search input and buttons", () => {
    render(<StudyBrowser />);
    expect(screen.getByPlaceholderText("Patient ID")).toBeInTheDocument();
    expect(screen.getByText("Search")).toBeInTheDocument();
    expect(screen.getByText("Clear")).toBeInTheDocument();
  });

  it("searches studies on button click", async () => {
    mockFetch.mockResolvedValue(
      mockDicomJsonResponse([
        {
          "0020000D": { vr: "UI", Value: ["1.2.3"] },
          "00100010": { vr: "PN", Value: [{ Alphabetic: "Test^Patient" }] },
          "00081030": { vr: "LO", Value: ["Chest CT"] },
          "00080061": { vr: "CS", Value: ["CT"] },
          "00080020": { vr: "DA", Value: ["20260701"] },
        },
      ]),
    );

    render(<StudyBrowser />);
    fireEvent.click(screen.getByText("Search"));

    await waitFor(() => {
      expect(screen.getByText("Chest CT")).toBeInTheDocument();
    });
    expect(screen.getByText("Test^Patient")).toBeInTheDocument();
  });

  it("clears results on clear button", async () => {
    mockFetch.mockResolvedValue(
      mockDicomJsonResponse([
        {
          "0020000D": { vr: "UI", Value: ["1.2.3"] },
        },
      ]),
    );

    render(<StudyBrowser />);
    fireEvent.click(screen.getByText("Search"));

    await waitFor(() => {
      expect(screen.getByText("1.2.3")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Clear"));
    expect(screen.queryByText("1.2.3")).not.toBeInTheDocument();
  });

  it("shows error message on fetch failure", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 });

    render(<StudyBrowser />);
    fireEvent.click(screen.getByText("Search"));

    await waitFor(
      () => {
        expect(screen.getByText("Server error")).toBeInTheDocument();
      },
      // request() retries GETs with exponential backoff (1s+2s+4s)
      { timeout: 12000 },
    );
  });
});
