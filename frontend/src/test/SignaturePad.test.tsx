import React, { useRef, useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import SignaturePad, { type SignaturePadHandle } from "../common/SignaturePad";

/**
 * Direct suite for the shared pad. The NursingPanel suite mocks this
 * component away — which once masked a real defect: the pad flagged itself
 * "signed" on bare mousedown, so a blank-canvas PNG data URL could pass
 * backend prefix validation and be stored as a consent signature (N-03).
 * These tests pin the real contract: has-signature only after an actual
 * stroke; clear resets; redraw re-enables.
 */

const makeCtxStub = () =>
  ({
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    clearRect: vi.fn(),
  }) as unknown as CanvasRenderingContext2D;

const PNG = "data:image/png;base64,AAAA";

function Harness({ onChange }: { onChange?: (has: boolean) => void }) {
  const padRef = useRef<SignaturePadHandle>(null);
  const [captured, setCaptured] = useState("");
  return (
    <div>
      <SignaturePad ref={padRef} onSignatureChange={onChange} />
      <button onClick={() => setCaptured(padRef.current?.capture() ?? "")}>capture</button>
      <span data-testid="captured">{captured}</span>
    </div>
  );
}

describe("SignaturePad", () => {
  let ctx: CanvasRenderingContext2D;
  let getContextSpy: ReturnType<typeof vi.spyOn>;
  let toDataURLSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    ctx = makeCtxStub();
    getContextSpy = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(ctx);
    toDataURLSpy = vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockReturnValue(PNG);
  });

  afterEach(() => {
    getContextSpy.mockRestore();
    toDataURLSpy.mockRestore();
  });

  const canvas = () => screen.getByRole("img", { name: /signature capture area/i });

  const draw = (from = 5) => {
    const pad = canvas();
    fireEvent.mouseDown(pad, { clientX: from, clientY: from });
    fireEvent.mouseMove(pad, { clientX: from + 20, clientY: from + 10 });
    fireEvent.mouseUp(pad);
  };

  it("does not report or capture a signature for a bare click", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    fireEvent.mouseDown(canvas());
    fireEvent.mouseUp(canvas());
    expect(onChange).not.toHaveBeenCalledWith(true);
    fireEvent.click(screen.getByRole("button", { name: "capture" }));
    expect(screen.getByTestId("captured")).toHaveTextContent("");
  });

  it("reports drawn only once a real segment exists and captures then", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    fireEvent.mouseDown(canvas(), { clientX: 5, clientY: 5 });
    // Still untouched after mousedown alone — the old defect.
    expect(onChange).not.toHaveBeenCalledWith(true);
    fireEvent.mouseMove(canvas(), { clientX: 25, clientY: 15 });
    expect(onChange).toHaveBeenCalledWith(true);
    fireEvent.click(screen.getByRole("button", { name: "capture" }));
    expect(screen.getByTestId("captured")).toHaveTextContent(PNG);
  });

  it("clear resets the pad to unsigned", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    draw();
    expect(onChange).toHaveBeenCalledWith(true);

    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(ctx.clearRect).toHaveBeenCalled();
    expect(onChange).toHaveBeenCalledWith(false);
    fireEvent.click(screen.getByRole("button", { name: "capture" }));
    expect(screen.getByTestId("captured")).toHaveTextContent("");
  });

  it("redraw after clear re-enables capture", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    draw();
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    draw(30);

    const calls = onChange.mock.calls.map((c) => c[0]);
    expect(calls).toEqual([true, false, true]);
    fireEvent.click(screen.getByRole("button", { name: "capture" }));
    expect(screen.getByTestId("captured")).toHaveTextContent(PNG);
  });
});
