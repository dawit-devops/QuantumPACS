import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import userEvent from "@testing-library/user-event";
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

describe("FlagCriticalModal submission (CR-5)", () => {
  it("sends the payload via `data` so request() serializes it as JSON", async () => {
    const user = userEvent.setup();

    (helpers.request as any).mockImplementationOnce(async (url: string) => {
      if (url.startsWith("notifications/critical/recipients")) return { data: [] };
      return { data: {} };
    });
    let captured: any = null;
    (helpers.request as any).mockImplementationOnce(async (url: string, opts: any) => {
      captured = { url, opts };
      return { data: { id: "crit-x" } };
    });

    renderWithApp(
      <FlagCriticalModal
        visible={true}
        exam={{ id: "ex1", accession_number: "ACC123", patient_id: "P123", patient_name: "Jane Doe" }}
        report={{ id: "rep1" }}
        onClose={() => {}}
        onSuccess={() => {}}
      />
    );

    await user.type(
      screen.getByPlaceholderText(/acute intracranial/i),
      "Acute Tension Pneumothorax"
    );
    await user.click(screen.getByRole("button", { name: /flag & notify/i }));

    await waitFor(() => expect(captured).not.toBeNull());

    expect(captured.url).toBe("notifications/critical");
    expect(captured.opts.method).toBe("POST");
    // The payload must be in `data` — request() JSON.stringifies options.data;
    // `body` is passed through untouched (the CR-5 bug sent "[object Object]").
    expect(captured.opts.data).toEqual(
      expect.objectContaining({
        report_id: "rep1",
        exam_id: "ex1",
        accession_number: "ACC123",
        patient_id: "P123",
        patient_name: "Jane Doe",
        finding_description: "Acute Tension Pneumothorax",
        recipient_role: "ed_physician",
      })
    );
    expect(captured.opts.body).toBeUndefined();
  });
});

describe("FlagCriticalModal recipient wiring (CR-7)", () => {
  it("loads recipients for the selected role and sends recipient_id when chosen", async () => {
    const user = userEvent.setup();

    (helpers.request as any).mockImplementationOnce(async (url: string) => {
      if (url.startsWith("notifications/critical/recipients")) {
        return { data: [{ id: "77", username: "dr_smith" }] };
      }
      return { data: {} };
    });

    let captured: any = null;
    (helpers.request as any).mockImplementationOnce(async (url: string, opts: any) => {
      captured = { url, opts };
      return { data: { id: "crit-x" } };
    });

    renderWithApp(
      <FlagCriticalModal
        visible={true}
        exam={{ id: "ex1", accession_number: "ACC123", patient_id: "P123", patient_name: "Jane Doe" }}
        report={{ id: "rep1" }}
        onClose={() => {}}
        onSuccess={() => {}}
      />
    );

    await user.type(
      screen.getByPlaceholderText(/acute intracranial/i),
      "Acute Pericardial Tamponade"
    );
    // Default role is ed_physician; the directory call populates the picker.
    await waitFor(() => {
      expect(helpers.request).toHaveBeenCalledWith(
        expect.stringContaining("notifications/critical/recipients?role=ed_physician")
      );
    });
    // antd Select renders options only while the dropdown is open.
    await user.click(screen.getByLabelText("Specific Recipient (optional)"));
    await waitFor(() => {
      expect(screen.getByText("dr_smith")).toBeDefined();
    });
    await user.click(screen.getByText("dr_smith"));
    await user.click(screen.getByRole("button", { name: /flag & notify/i }));

    await waitFor(() => expect(captured).not.toBeNull());

    expect(captured.url).toBe("notifications/critical");
    // CR-7: the chosen user must ride along as recipient_id (role stays for
    // the fallback display).
    expect(captured.opts.data).toEqual(
      expect.objectContaining({
        recipient_role: "ed_physician",
        recipient_id: "77",
      })
    );
  });

  it("omits recipient_id when no user is chosen (role fallback)", async () => {
    const user = userEvent.setup();

    (helpers.request as any).mockImplementationOnce(async () => {
      return { data: [] };
    });

    let captured: any = null;
    (helpers.request as any).mockImplementationOnce(async (url: string, opts: any) => {
      captured = { url, opts };
      return { data: { id: "crit-y" } };
    });

    renderWithApp(
      <FlagCriticalModal
        visible={true}
        exam={{ id: "ex1", accession_number: "ACC123", patient_id: "P123" }}
        report={{ id: "rep1" }}
        onClose={() => {}}
        onSuccess={() => {}}
      />
    );

    await user.type(
      screen.getByPlaceholderText(/acute intracranial/i),
      "Acute Ischemic Stroke"
    );
    await user.click(screen.getByRole("button", { name: /flag & notify/i }));

    await waitFor(() => expect(captured).not.toBeNull());
    expect(helpers.request).toHaveBeenCalledWith(
      expect.stringContaining("notifications/critical/recipients?role=ed_physician")
    );

    expect(captured.opts.data.recipient_role).toBe("ed_physician");
    expect(captured.opts.data.recipient_id).toBeUndefined();
  });
});
