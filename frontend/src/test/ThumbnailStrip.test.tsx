import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import ThumbnailStrip from "../detail/ThumbnailStrip";
import { API_URL } from "../config";

const mockFiles = [
  { id: 1, name: "image1.dcm" },
  { id: 2, name: "image2.dcm" },
  { id: 3, name: "image3.dcm" },
];

describe("ThumbnailStrip", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads thumbnails without appending a token to the URL", () => {
    const srcs: string[] = [];
    class FakeImage {
      set src(v: string) {
        srcs.push(v);
      }
      get src() {
        return srcs[srcs.length - 1];
      }
    }
    vi.stubGlobal("Image", FakeImage);

    render(
      <ThumbnailStrip files={mockFiles} currentFileId="1" onSelect={vi.fn()} />,
    );

    expect(srcs).toEqual([
      `${API_URL}/files/1/thumbnail`,
      `${API_URL}/files/2/thumbnail`,
      `${API_URL}/files/3/thumbnail`,
    ]);
    expect(srcs.join(" ")).not.toContain("token=");
  });
  it("renders null when files is null", () => {
    const { container } = render(
      <ThumbnailStrip
        files={null as any}
        currentFileId="1"
        onSelect={vi.fn()}
      />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders null when files has only one item", () => {
    const { container } = render(
      <ThumbnailStrip
        files={[{ id: 1, name: "single.dcm" }]}
        currentFileId="1"
        onSelect={vi.fn()}
      />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders a thumbnail option for each file", () => {
    render(
      <ThumbnailStrip files={mockFiles} currentFileId="1" onSelect={vi.fn()} />,
    );
    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(3);
  });

  it("marks the current file as active", () => {
    render(
      <ThumbnailStrip files={mockFiles} currentFileId="2" onSelect={vi.fn()} />,
    );
    const options = screen.getAllByRole("option");
    expect(options[1].className).toContain("active");
    expect(options[0].className).not.toContain("active");
    expect(options[2].className).not.toContain("active");
  });

  it("calls onSelect with index when clicked", () => {
    const onSelect = vi.fn();
    render(
      <ThumbnailStrip
        files={mockFiles}
        currentFileId="1"
        onSelect={onSelect}
      />,
    );
    const options = screen.getAllByRole("option");
    fireEvent.click(options[2]);
    expect(onSelect).toHaveBeenCalledWith(2);
  });
});
