import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import ResizableSplit from "../common/ResizableSplit";

function renderSplit(initialRatio = 0.5) {
  return render(
    <ResizableSplit
      storageKey="test-split"
      initialRatio={initialRatio}
      left={<div>Left pane</div>}
      right={<div>Right pane</div>}
      ariaLabel="Resize report panel"
    />,
  );
}

describe("ResizableSplit", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders both panes and a labeled separator", () => {
    renderSplit();
    expect(screen.getByText("Left pane")).toBeInTheDocument();
    expect(screen.getByText("Right pane")).toBeInTheDocument();
    const handle = screen.getByRole("separator", {
      name: "Resize report panel",
    });
    expect(handle).toHaveAttribute("aria-orientation", "vertical");
    expect(handle).toHaveAttribute("tabindex", "0");
  });

  it("applies the initial ratio to the left pane", () => {
    renderSplit(0.6);
    const panes = document.querySelectorAll(".resizable-split-pane");
    expect(panes[0]).toHaveStyle({ flexBasis: "60%" });
    expect(panes[1]).toHaveStyle({ flex: "1" });
  });

  it("resizes the left pane with the arrow keys and persists the ratio", () => {
    renderSplit(0.5);
    const handle = screen.getByRole("separator", {
      name: "Resize report panel",
    });
    fireEvent.keyDown(handle, { key: "ArrowLeft" });
    const panes = document.querySelectorAll(".resizable-split-pane");
    expect(panes[0]).toHaveStyle({ flexBasis: "48%" });
    expect(localStorage.getItem("test-split")).toBe("0.48");
  });

  it("restores a persisted ratio over the initial one", () => {
    localStorage.setItem("test-split", "0.7");
    renderSplit(0.5);
    const panes = document.querySelectorAll(".resizable-split-pane");
    expect(panes[0]).toHaveStyle({ flexBasis: "70%" });
  });
});
