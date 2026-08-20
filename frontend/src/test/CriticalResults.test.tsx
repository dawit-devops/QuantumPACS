import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import { FlagCriticalModal, CriticalResultsList } from "../radiologist/CriticalResults";
import * as helpers from "../helpers";

vi.mock("../helpers", async () => {
  const actual = await vi.importActual("../helpers");
  return {
    ...actual,
    request: vi.fn(),
  };
});

describe("CriticalResults Component Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders FlagCriticalModal when visible", async () => {
    renderWithApp(
      <FlagCriticalModal
        visible={true}
        exam={{ id: "ex1", accession_number: "ACC123", patient_id: "P123" }}
        report={{ id: "rep1" }}
        onClose={() => {}}
        onSuccess={() => {}}
      />
    );
    expect(screen.getByText("Flag Critical Result")).toBeDefined();
    expect(screen.getByText("Critical Finding Description")).toBeDefined();
  });

  it("renders CriticalResultsList table with data", async () => {
    (helpers.request as any).mockResolvedValueOnce({
      data: [
        {
          id: "crit-1",
          accession_number: "ACC-CRIT-99",
          patient_id: "PAT-99",
          patient_name: "John Critical",
          finding_description: "Acute Stroke",
          status: "flagged",
          recipient_role: "ed_physician",
          flagged_at: "2026-08-20T03:00:00Z",
        },
      ],
    });

    renderWithApp(<CriticalResultsList />);

    await waitFor(() => {
      expect(screen.getByText("Critical Findings & Alerts")).toBeDefined();
      expect(screen.getByText("ACC-CRIT-99")).toBeDefined();
      expect(screen.getByText("Acute Stroke")).toBeDefined();
      expect(screen.getByText("FLAGGED")).toBeDefined();
    });
  });
});
