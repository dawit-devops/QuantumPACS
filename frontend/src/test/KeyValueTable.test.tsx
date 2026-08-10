import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import KeyValueTable from "../detail/KeyValueTable";

const sampleMeta = {
  PatientName: "Doe^John",
  StudyDate: "20240101",
  Modality: "CT",
};

describe("KeyValueTable", () => {
  it("renders sorted meta rows", () => {
    render(<KeyValueTable file={{ id: 1, meta: sampleMeta }} />);
    const rows = screen.getAllByRole("row");
    // header row + one row per tag, sorted by key
    expect(rows).toHaveLength(4);
    const cells = screen.getAllByRole("cell").map((c) => c.textContent);
    expect(cells).toEqual([
      "Modality",
      "CT",
      "PatientName",
      "Doe^John",
      "StudyDate",
      "20240101",
    ]);
  });

  it("filters rows by prefix search, case-insensitively", () => {
    render(<KeyValueTable file={{ id: 1, meta: sampleMeta }} />);
    fireEvent.change(screen.getByPlaceholderText("Search..."), {
      target: { value: "patient" },
    });
    expect(screen.getAllByRole("row")).toHaveLength(2);
    expect(screen.getByText("PatientName")).toBeInTheDocument();
    expect(screen.queryByText("Modality")).not.toBeInTheDocument();
  });

  // (R1-05) The old two-effect implementation reset the search box on every
  // new file; the derived-row version keeps the filter across file changes.
  it("keeps the search filter when the file changes", () => {
    const { rerender } = render(
      <KeyValueTable file={{ id: 1, meta: sampleMeta }} />,
    );
    fireEvent.change(screen.getByPlaceholderText("Search..."), {
      target: { value: "study" },
    });
    rerender(
      <KeyValueTable
        file={{ id: 2, meta: { SeriesNumber: "7", StudyDate: "20240202" } }}
      />,
    );
    expect(screen.getByPlaceholderText("Search...")).toHaveValue("study");
    expect(screen.getAllByRole("row")).toHaveLength(2);
    expect(screen.getByText("StudyDate")).toBeInTheDocument();
    expect(screen.queryByText("SeriesNumber")).not.toBeInTheDocument();
  });

  it("renders an empty table when meta is missing", () => {
    render(<KeyValueTable file={{ id: 1 }} />);
    // header row + antd's "No data" placeholder row
    expect(screen.getAllByRole("row")).toHaveLength(2);
  });
});
