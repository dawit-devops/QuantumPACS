import { useCallback, useEffect, useState } from "react";
import { request } from "../helpers";
import type { FileStudy, FileSeries, FileNode } from "../api/files";

// The images endpoint reuses the /files/{id} tree shape
// (patient.studies[].series[].files[]) so the console can hand the same
// props to CornerstoneElement that Detail does.
export interface ExamImagingPatient {
  id?: number;
  patient_id?: string;
  name?: string;
  studies?: FileStudy[];
}

interface ExamImagingResponse {
  imaging: boolean;
  patient?: ExamImagingPatient;
}

export interface ExamImagingState {
  exam: any | null;
  report: any | null;
  imaging: boolean;
  studies: FileStudy[];
  selectedStudy: FileStudy | null;
  selectedSeries: FileSeries | null;
  selectedFile: FileNode | null;
  loading: boolean;
  error: string | null;
  setReport: (report: any) => void;
  selectStudy: (study: FileStudy) => void;
  selectSeries: (series: FileSeries) => void;
  selectFile: (index: number) => void;
}

/**
 * Loads the report + imaging tree for a reading exam in parallel and keeps
 * the selected study/series/file derived from the tree. Selection state is
 * stored by id so a later tree reload keeps the user's place where possible.
 */
export function useExamImaging(examId: string | undefined): ExamImagingState {
  const [exam, setExam] = useState<any | null>(null);
  const [report, setReport] = useState<any | null>(null);
  const [patient, setPatient] = useState<ExamImagingPatient | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [studyId, setStudyId] = useState<number | null>(null);
  const [seriesId, setSeriesId] = useState<number | null>(null);
  const [fileId, setFileId] = useState<number | null>(null);

  const load = useCallback(() => {
    if (!examId) return;
    setLoading(true);
    setError(null);
    Promise.all([
      request(`reports/${examId}`),
      request(`reports/${examId}/images`),
    ])
      .then(([reportRes, imgRes]: any[]) => {
        setExam(reportRes?.data?.exam ?? null);
        setReport(reportRes?.data?.report ?? null);
        const images: ExamImagingResponse | undefined = imgRes?.data;
        setPatient(images?.imaging ? (images.patient ?? null) : null);
        setLoading(false);
      })
      .catch((e: any) => {
        setLoading(false);
        setError(e.message);
      });
  }, [examId]);

  useEffect(() => {
    load();
  }, [load]);

  const studies = patient?.studies ?? [];
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

  const selectStudy = useCallback((study: FileStudy) => {
    setStudyId(study.id);
    setSeriesId(null);
    setFileId(null);
  }, []);

  const selectSeries = useCallback((series: FileSeries) => {
    setSeriesId(series.id);
    setFileId(null);
  }, []);

  // CornerstoneElement calls changeFile(index) — an index into the current
  // series' files array (slider + thumbnail strip + arrow keys).
  const selectFile = useCallback(
    (index: number) => {
      const files = selectedSeries?.files ?? [];
      const target = files[index];
      if (target) setFileId(target.id);
    },
    [selectedSeries],
  );

  return {
    exam,
    report,
    imaging: !!patient,
    studies,
    selectedStudy,
    selectedSeries,
    selectedFile,
    loading,
    error,
    setReport,
    selectStudy,
    selectSeries,
    selectFile,
  };
}
