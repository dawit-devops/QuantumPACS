import React, { Suspense, useState } from "react";
import { Spin, Alert } from "antd";
import { API_URL } from "../config";
import SeriesNavigator from "../radiologist/SeriesNavigator";
import type { FileStudy, FileSeries, FileNode } from "../api/files";
import "./ExamViewport.css";

// C11 (Sprint D): the exam console mounts the real viewer when the exam has
// DICOM. Reuses the reading console's proven pattern — SeriesNavigator +
// CornerstoneElement over the file-tree shape (`patient.studies[].series[].
// files[]`) — but the tree arrives with the exam payload, so there is no
// second round-trip and no REPORT_READ requirement.
const CornerstoneElement = React.lazy(
  () => import("../detail/CornerstoneElement"),
);

interface ExamViewportProps {
  patient: { studies?: FileStudy[] };
  patientName?: string;
  patientId?: string;
  examModality?: string;
}

export default function ExamViewport({
  patient,
  patientName,
  patientId,
  examModality,
}: ExamViewportProps) {
  const studies: FileStudy[] = patient?.studies ?? [];
  const [studyId, setStudyId] = useState<number | null>(null);
  const [seriesId, setSeriesId] = useState<number | null>(null);
  const [fileId, setFileId] = useState<number | null>(null);

  // Selection is derived from the tree by id (same strategy as the reading
  // console) so a reload keeps the user's place where possible.
  const selectedStudy =
    studies.find((s) => s.id === studyId) ?? studies[0] ?? null;
  const selectedSeries =
    selectedStudy?.series?.find((s) => s.id === seriesId) ??
    selectedStudy?.series?.[0] ??
    null;
  const selectedFile =
    selectedSeries?.files?.find((f) => f.id === fileId) ??
    selectedSeries?.files?.[0] ??
    null;

  const files: FileNode[] = selectedSeries?.files ?? [];
  const fileIndex = files.findIndex((f) => f.id === selectedFile?.id);

  const selectStudy = (study: FileStudy) => {
    setStudyId(study.id);
    setSeriesId(null);
    setFileId(null);
  };
  const selectSeries = (series: FileSeries) => {
    setSeriesId(series.id);
    setFileId(null);
  };
  const selectFile = (index: number) => {
    const target = files[index];
    if (target) setFileId(target.id);
  };

  const imageUrl = selectedFile
    ? `wadouri:${API_URL}/files/${selectedFile.id}/data`
    : "";

  // CornerstoneElement's `file` prop — the tree node enriched with modality
  // and patient context for its metadata panel, mirroring ReadingConsole.
  const ceFile = selectedFile
    ? {
        ...selectedFile,
        modality: selectedSeries?.modality || examModality || "",
        patient: patientName
          ? { name: patientName, patient_id: patientId }
          : undefined,
        study: selectedStudy?.description || selectedStudy?.study_id || "",
        series:
          selectedSeries?.description || String(selectedSeries?.number ?? ""),
      }
    : { id: 0 };

  return (
    <div className="exam-viewport">
      <SeriesNavigator
        studies={studies}
        selectedStudy={selectedStudy}
        selectedSeries={selectedSeries}
        fileIndex={Math.max(0, fileIndex)}
        files={files}
        onStudyChange={selectStudy}
        onSeriesChange={selectSeries}
        onFileChange={selectFile}
      />
      <div className="exam-viewport-body">
        {selectedFile ? (
          <Suspense
            fallback={
              <Spin
                size="large"
                style={{
                  display: "flex",
                  justifyContent: "center",
                  marginTop: 100,
                }}
              />
            }
          >
            <CornerstoneElement
              file={ceFile}
              files={files}
              changeFile={selectFile}
              image={imageUrl}
              progressive={true}
              visible
            />
          </Suspense>
        ) : (
          <Alert
            type="info"
            showIcon
            title="No images in this series"
            style={{ margin: 16 }}
          />
        )}
      </div>
    </div>
  );
}
