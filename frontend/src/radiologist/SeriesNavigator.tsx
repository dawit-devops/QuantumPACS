import React from "react";
import { Select, Slider } from "antd";
import { FileImageOutlined } from "@ant-design/icons";
import type { FileStudy, FileSeries, FileNode } from "../api/files";
import "./SeriesNavigator.css";

interface SeriesNavigatorProps {
  studies: FileStudy[];
  selectedStudy: FileStudy | null;
  selectedSeries: FileSeries | null;
  /** Index of the selected instance within the selected series' files. */
  fileIndex: number;
  files: FileNode[];
  onStudyChange: (study: FileStudy) => void;
  onSeriesChange: (series: FileSeries) => void;
  onFileChange: (index: number) => void;
}

// In-console study/series navigation (the console lifts what Detail builds
// in its breadcrumbs). The series dropdown drives CornerstoneElement's stack
// swap; the slider mirrors its built-in slider for one-glance instance
// orientation next to the series context.
export default function SeriesNavigator({
  studies,
  selectedStudy,
  selectedSeries,
  fileIndex,
  files,
  onStudyChange,
  onSeriesChange,
  onFileChange,
}: SeriesNavigatorProps) {
  const series = selectedStudy?.series ?? [];
  return (
    <div
      className="series-navigator"
      role="toolbar"
      aria-label="Series navigation"
    >
      {studies.length > 1 && (
        <Select
          aria-label="Study"
          size="small"
          style={{ minWidth: 180 }}
          value={selectedStudy?.id}
          onChange={(id: number) => {
            const study = studies.find((s) => s.id === id);
            if (study) onStudyChange(study);
          }}
          options={studies.map((s) => ({
            value: s.id,
            label: `Study ${s.study_id ?? ""}${
              s.description ? ` — ${s.description}` : ""
            }`,
          }))}
        />
      )}
      <Select
        aria-label="Series"
        size="small"
        style={{ minWidth: 220 }}
        value={selectedSeries?.id}
        onChange={(id: number) => {
          const sr = series.find((s) => s.id === id);
          if (sr) onSeriesChange(sr);
        }}
        options={series.map((sr) => ({
          value: sr.id,
          label: `Series ${sr.number ?? ""}${
            sr.modality ? ` (${sr.modality})` : ""
          }${sr.description ? ` — ${sr.description}` : ""}`,
        }))}
      />
      {files.length > 1 && (
        <div className="series-navigator-slider">
          <Slider
            min={0}
            max={files.length - 1}
            value={fileIndex}
            tooltip={{ formatter: (v: any) => files[v]?.name }}
            onChange={onFileChange}
            aria-label={`Instance ${fileIndex + 1} of ${files.length}`}
          />
          <span className="series-navigator-count" aria-hidden="true">
            <FileImageOutlined /> {fileIndex + 1}/{files.length}
          </span>
        </div>
      )}
    </div>
  );
}
