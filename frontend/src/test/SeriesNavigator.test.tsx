import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import SeriesNavigator from "../radiologist/SeriesNavigator";
import type { FileStudy, FileSeries } from "../api/files";

const study1: FileStudy = {
  id: 1,
  study_id: "ST-1",
  description: "Chest",
  accession_number: "ACC1",
  series: [
    {
      id: 10,
      study_id: 1,
      number: 1,
      modality: "CT",
      description: "Axial",
      files: [
        { id: 100, name: "IM1" },
        { id: 101, name: "IM2" },
        { id: 102, name: "IM3" },
      ],
    },
    {
      id: 11,
      study_id: 1,
      number: 2,
      modality: "CT",
      description: "Coronal",
      files: [{ id: 200, name: "IM4" }],
    },
  ],
};

const study2: FileStudy = {
  id: 2,
  study_id: "ST-2",
  description: "Prior",
  series: [{ id: 20, study_id: 2, number: 1, files: [] }],
};

function renderNav(opts: {
  studies?: FileStudy[];
  series?: FileSeries;
  onSeriesChange?: (s: FileSeries) => void;
  onFileChange?: (i: number) => void;
} = {}) {
  const studies = opts.studies ?? [study1];
  const selectedStudy = studies[0];
  const selectedSeries = opts.series ?? study1.series![0];
  return render(
    <SeriesNavigator
      studies={studies}
      selectedStudy={selectedStudy}
      selectedSeries={selectedSeries}
      fileIndex={0}
      files={selectedSeries.files ?? []}
      onStudyChange={vi.fn()}
      onSeriesChange={opts.onSeriesChange ?? vi.fn()}
      onFileChange={opts.onFileChange ?? vi.fn()}
    />,
  );
}

describe("SeriesNavigator", () => {
  it("renders the series dropdown with the current series selected", () => {
    renderNav();
    const select = screen.getByLabelText("Series");
    expect(select).toBeInTheDocument();
    expect(screen.getByText(/Series 1/)).toBeInTheDocument();
  });

  it("shows the instance slider only for multi-file series", () => {
    const { rerender } = renderNav();
    expect(
      document.querySelector(".series-navigator-slider"),
    ).toBeInTheDocument();
    expect(screen.getByText("1/3")).toBeInTheDocument();

    rerender(
      <SeriesNavigator
        studies={[study1]}
        selectedStudy={study1}
        selectedSeries={study1.series![1]}
        fileIndex={0}
        files={study1.series![1].files ?? []}
        onStudyChange={vi.fn()}
        onSeriesChange={vi.fn()}
        onFileChange={vi.fn()}
      />,
    );
    expect(
      document.querySelector(".series-navigator-slider"),
    ).not.toBeInTheDocument();
  });

  it("omits the study dropdown when only one study is present", () => {
    renderNav();
    expect(screen.queryByLabelText("Study")).not.toBeInTheDocument();
  });

  it("shows the study dropdown when multiple studies are present", () => {
    renderNav({ studies: [study1, study2] });
    expect(screen.getByLabelText("Study")).toBeInTheDocument();
  });

  it("fires onSeriesChange with the picked series", () => {
    const onSeriesChange = vi.fn();
    renderNav({ onSeriesChange });
    fireEvent.mouseDown(screen.getByLabelText("Series"));
    fireEvent.click(screen.getByText(/Series 2/));
    expect(onSeriesChange).toHaveBeenCalledWith(
      expect.objectContaining({ id: 11 }),
    );
  });

  it("fires onFileChange with the slider index", () => {
    const onFileChange = vi.fn();
    renderNav({ onFileChange });
    // The antd Slider fires onChange with the numeric value on its handle
    // (it reads e.which || e.keyCode, so both are passed explicitly).
    const handle = document.querySelector(".ant-slider-handle");
    expect(handle).not.toBeNull();
    fireEvent.keyDown(handle as Element, {
      key: "ArrowRight",
      keyCode: 39,
      which: 39,
    });
    expect(onFileChange).toHaveBeenCalled();
  });
});
