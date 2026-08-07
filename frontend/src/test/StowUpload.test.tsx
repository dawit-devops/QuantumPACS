import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import { describe, it, expect, vi, beforeEach } from "vitest";
import StowUpload from "../dicomweb/StowUpload";

const mockStoreInstances = vi.hoisted(() => vi.fn());
vi.mock("../api/studies", () => ({
  storeInstances: mockStoreInstances,
  downloadStudyArchive: vi.fn(),
  wadoRsUrl: vi.fn(),
}));
vi.mock("../common/base", () => ({
  __esModule: true,
  default: (c: React.ComponentType) => (props: any) =>
    React.createElement(c as React.ComponentType<any>, props),
}));

function makeDcmFile(name = "smoke.dcm", size = 1024): File {
  const f = new File([new Uint8Array(size)], name, {
    type: "application/dicom",
  });
  return f;
}

describe("StowUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStoreInstances.mockResolvedValue({
      referenced: [
        { "00081150": { Value: ["1.2.3"] } },
        { "00081150": { Value: ["4.5.6"] } },
      ],
      failed: [],
    });
  });

  it("renders the drop zone", () => {
    renderWithApp(<StowUpload />);
    expect(screen.getByText(/Drag & drop .dcm files here/)).toBeInTheDocument();
  });

  it("lists selected files and stores them", async () => {
    const { container } = renderWithApp(<StowUpload />);
    const input = container.querySelector("#stow-file-input")!;
    fireEvent.change(input, {
      target: { files: [makeDcmFile("a.dcm"), makeDcmFile("b.dcm")] },
    });
    expect(await screen.findByText("a.dcm")).toBeInTheDocument();
    expect(screen.getByText("b.dcm")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Store to PACS"));
    await waitFor(() => expect(mockStoreInstances).toHaveBeenCalled());
    const files: File[] = mockStoreInstances.mock.calls[0][0];
    expect(files.map((f) => f.name)).toEqual(["a.dcm", "b.dcm"]);

    expect(await screen.findByText("2 instance(s) stored")).toBeInTheDocument();
  });

  it("rejects non-dcm files", async () => {
    const { container } = renderWithApp(<StowUpload />);
    const input = container.querySelector("#stow-file-input")!;
    fireEvent.change(input, {
      target: { files: [makeDcmFile("notes.txt")] },
    });
    await waitFor(() => {
      const btn = screen.getByText("Store to PACS").closest("button");
      expect(btn).toBeDefined();
      expect(btn).toBeDisabled();
    });
  });

  it("shows error result when all instances fail", async () => {
    mockStoreInstances.mockResolvedValue({
      referenced: [],
      failed: [{ "00081155": { Value: ["1.2.3"] } }],
    });
    const { container } = renderWithApp(<StowUpload />);
    const input = container.querySelector("#stow-file-input")!;
    fireEvent.change(input, {
      target: { files: [makeDcmFile("bad.dcm")] },
    });
    fireEvent.click(await screen.findByText("Store to PACS"));
    expect(await screen.findByText("Nothing stored")).toBeInTheDocument();
  });

  it("surfaces store errors", async () => {
    mockStoreInstances.mockRejectedValue(new Error("STOW-RS failed (413)"));
    const { container } = renderWithApp(<StowUpload />);
    const input = container.querySelector("#stow-file-input")!;
    fireEvent.change(input, {
      target: { files: [makeDcmFile("big.dcm")] },
    });
    fireEvent.click(await screen.findByText("Store to PACS"));
    await waitFor(() =>
      expect(screen.queryByText("STOW-RS failed (413)")).toBeTruthy(),
    );
  });
});
