import React, { useState, useEffect, useRef } from "react";
import { API_URL } from "../config";
import "./ThumbnailStrip.css";

interface ThumbnailStripProps {
  files: any[];
  currentFileId: string;
  onSelect: (index: number) => void;
}

export default function ThumbnailStrip({
  files,
  currentFileId,
  onSelect,
}: ThumbnailStripProps) {
  if (!files || files.length <= 1) return null;

  return (
    // (R1-05) Plain tab-ordered buttons instead of a listbox/option pair —
    // the listbox contract demands arrow-key navigation that was never
    // implemented, so it misled AT users into expecting it.
    <div className="thumbnail-strip" aria-label="Series thumbnails">
      {files.map((f, index) => (
        <ThumbnailItem
          key={f.id}
          file={f}
          index={index}
          isActive={String(f.id) === String(currentFileId)}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}

function ThumbnailItem({
  file,
  index,
  isActive,
  onSelect,
}: {
  file: any;
  index: number;
  isActive: boolean;
  onSelect: (index: number) => void;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const containerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    // (P-M5) Lazy loading: only fetch the thumbnail once the item is near the
    // viewport. Without this, a long series fires one 200-GET per instance on
    // mount. The active (currently displayed) thumbnail loads immediately.
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
      // Prefetch slightly outside the viewport so scrolling feels instant.
      { rootMargin: "200px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file.id, isActive]);

  const loadThumbnail = () => {
    if (src || error) return;
    // Same-site image fetch; the HttpOnly token cookie authenticates it, so
    // no token is appended to the URL (S1-D).
    const url = `${API_URL}/files/${file.id}/thumbnail`;
    const img = new Image();
    img.onload = () => setSrc(url);
    img.onerror = () => setError(true);
    img.src = url;
  };

  return (
    <button
      ref={containerRef}
      className={`thumbnail-item ${isActive ? "active" : ""}`}
      onClick={() => onSelect(index)}
      title={file.name}
      aria-label={`${file.name}${isActive ? " (active)" : ""}`}
    >
      {src && !error ? (
        <img src={src} alt={file.name} className="thumbnail-image" />
      ) : (
        <div
          className="thumbnail-placeholder"
          aria-label={error ? "Failed to load thumbnail" : "Loading thumbnail"}
        >
          {error ? "!" : "..."}
        </div>
      )}
    </button>
  );
}
