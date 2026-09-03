import React, { useState, useEffect, useRef } from "react";
import { API_URL } from "../config";
import type { FileStudy, FileSeries } from "../api/files";
import type { PhaseGroup } from "./phaseGroups";
import { groupByPhase, PHASE_COLORS } from "./phaseGroups";
import "./ReadingThumbnailStrip.css";

interface ReadingThumbnailStripProps {
  studies: FileStudy[];
  selectedStudy: FileStudy | null;
  selectedSeries: FileSeries | null;
  activePhaseKey: string | null;
  onSelectPhase: (group: PhaseGroup) => void;
}

// §4.2 "PRIOR · <date>" divider — beneath the current study's phase groups,
// a dashed divider signals that comparison studies exist without building the
// full comparison state out. Any study other than the selected one is treated
// as a prior (the console loads multiple studies per exam).
const PRIOR_LABEL = "PRIOR";

// Left-hand phase rail: series are stacked into acquisition-protocol phase
// groups (scout, non-contrast, arterial, portal venous, delayed, reformat,
// dose…). Each group shows ONE representative thumbnail per series. Clicking
// any thumbnail in a group loads the ENTIRE phase set into the main viewport
// (all series of the phase flattened in acquisition order), so the
// radiologist can scroll, annotate and capture key images across the whole
// phase at once.
export default function ReadingThumbnailStrip({
  studies,
  selectedStudy,
  selectedSeries,
  activePhaseKey,
  onSelectPhase,
}: ReadingThumbnailStripProps) {
  if (!selectedStudy?.series?.length) return null;
  const groups = groupByPhase(selectedStudy.series);
  // Studies other than the currently selected one are earlier/comparison
  // priors; surface them as a labeled divider so comparison is discoverable
  // even before full dual-state comparison is built.
  const priors = studies.filter((s) => String(s.id) !== String(selectedStudy.id));

  return (
    <div
      className="reading-thumbnails"
      role="listbox"
      aria-label="Series image thumbnails"
    >
      {groups.map((group) => (
        <PhaseGroupView
          key={group.key}
          group={group}
          isActive={group.key === activePhaseKey}
          isSeriesActive={(s) => String(s.id) === String(selectedSeries?.id)}
          onSelectPhase={onSelectPhase}
        />
      ))}
      {priors.length > 0 && (
        <div className="reading-thumbnails-priors" aria-label="Prior studies">
          <div className="reading-thumbnails-divider">
            <span className="reading-thumbnails-divider-label">
              {PRIOR_LABEL} · {priors.length}
            </span>
          </div>
          {priors.map((prior) => {
            const priorModality = prior.series?.[0]?.modality || "IMG";
            return (
              <div
                key={prior.id}
                className="reading-thumbnails-prior"
                title={`Prior ${priorModality} ${prior.description || ""}`}
              >
                <span className="reading-thumbnails-prior-mod">
                  {priorModality}
                </span>
                <span className="reading-thumbnails-prior-desc">
                  {prior.description || `Prior ${prior.id}`}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function PhaseGroupView({
  group,
  isActive,
  isSeriesActive,
  onSelectPhase,
}: {
  group: PhaseGroup;
  isActive: boolean;
  isSeriesActive: (s: FileSeries) => boolean;
  onSelectPhase: (group: PhaseGroup) => void;
}) {
  const color = PHASE_COLORS[group.key];
  const totalSlices = group.series.reduce((s, x) => s + (x.files?.length ?? 0), 0);

  return (
    <div className={`reading-thumbnail-phase${isActive ? " active" : ""}`}>
      <button
        type="button"
        className="reading-thumbnail-phase-label"
        style={{ borderLeftColor: color }}
        onClick={() => onSelectPhase(group)}
        title={`View entire ${group.label} phase (${totalSlices} images)`}
        aria-label={`View ${group.label} phase, ${totalSlices} images`}
      >
        <span className="reading-thumbnail-phase-name">{group.label}</span>
        <span className="reading-thumbnail-phase-stats">{totalSlices}</span>
      </button>
      {group.series.map((series) => {
        const files = series.files ?? [];
        const rep = files[0];
        if (!rep) return null;
        return (
          <div
            key={series.id}
            className={`reading-thumbnail-series${isSeriesActive(series) ? " active" : ""}`}
          >
            <SeriesThumbnail
              file={rep}
              sliceCount={files.length}
              isActive={isSeriesActive(series)}
              onSelect={() => onSelectPhase(group)}
            />
            <div className="reading-thumbnail-series-label">
              <span className="reading-thumbnail-series-number">
                {series.number ?? "—"}
              </span>
              {series.modality && (
                <span className="reading-thumbnail-series-mod">
                  {series.modality}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SeriesThumbnail({
  file,
  isActive,
  sliceCount,
  onSelect,
}: {
  file: any;
  isActive: boolean;
  sliceCount: number;
  onSelect: () => void;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const containerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (isActive) {
      loadThumbnail();
      return;
    }
    const el = containerRef.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      loadThumbnail();
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          observer.disconnect();
          loadThumbnail();
        }
      },
      { rootMargin: "300px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [file.id, isActive]);

  const loadThumbnail = () => {
    if (src || error) return;
    const url = `${API_URL}/files/${file.id}/thumbnail`;
    const img = new Image();
    img.onload = () => setSrc(url);
    img.onerror = () => setError(true);
    img.src = url;
  };

  return (
    <button
      ref={containerRef}
      className={`reading-thumbnail-item${isActive ? " active" : ""}`}
      onClick={onSelect}
      title={file.name}
      aria-label={`${file.name}${isActive ? " (active)" : ""}`}
      aria-selected={isActive}
      role="option"
    >
      {src && !error ? (
        <img src={src} alt={file.name} className="reading-thumbnail-image" />
      ) : (
        <div
          className="reading-thumbnail-placeholder"
          aria-label={error ? "Failed to load thumbnail" : "Loading thumbnail"}
        >
          {error ? "!" : "..."}
        </div>
      )}
      {sliceCount > 1 && (
        <span className="reading-thumbnail-slice-count">{sliceCount}</span>
      )}
    </button>
  );
}