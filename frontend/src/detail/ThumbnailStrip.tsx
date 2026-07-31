import React, { useState, useEffect } from "react";
import { API_URL } from "../config";
import { getAccessToken } from "../helpers";
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
    <div
      className="thumbnail-strip"
      role="listbox"
      aria-label="Series thumbnails"
    >
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

  useEffect(() => {
    const token = getAccessToken();
    const url = `${API_URL}/files/${file.id}/thumbnail${token ? `?token=${token}` : ""}`;
    const img = new Image();
    img.onload = () => setSrc(url);
    img.onerror = () => setError(true);
    img.src = url;
  }, [file.id]);

  return (
    <button
      className={`thumbnail-item ${isActive ? "active" : ""}`}
      onClick={() => onSelect(index)}
      title={file.name}
      aria-label={`${file.name}${isActive ? " (active)" : ""}`}
      aria-selected={isActive}
      role="option"
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
