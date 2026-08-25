import React, { forwardRef, useImperativeHandle, useRef } from "react";
import { Button, Space, Typography } from "antd";

const { Text } = Typography;

export interface SignaturePadHandle {
  /** PNG data URL of the current canvas contents ('' when nothing drawn). */
  capture: () => string;
  clear: () => void;
}

interface Props {
  /** Called whenever the signature transitions between empty and drawn. */
  onSignatureChange?: (hasSignature: boolean) => void;
  width?: number;
  height?: number;
  /** Helper line under the pad (kiosk uses patient-facing copy). */
  hint?: string;
  /** Label for the built-in clear button. */
  clearLabel?: string;
  /** data-testid for the canvas, for suites that drive real strokes. */
  testId?: string;
}

/**
 * Reusable signature capture (spec §2.12 lists this as a shared component).
 * Drawing handlers are cloned from the kiosk consent pad (CheckIn.tsx):
 * the drawing flag lives in a ref so a rapid mouseDown -> mouseMove reads
 * it synchronously.
 *
 * has-signature is only reported once a real segment reaches the canvas —
 * a bare click must not count as a signature, because toDataURL() of a
 * blank canvas yields a perfectly valid PNG data URL that would defeat any
 * downstream "signature present" check (consent integrity, spec N-03).
 */
const SignaturePad = forwardRef<SignaturePadHandle, Props>(
  (
    {
      onSignatureChange,
      width = 420,
      height = 140,
      hint = "Draw the signature above",
      clearLabel = "Clear",
      testId,
    },
    ref
  ) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const drawingRef = useRef(false);
    // Count of segments actually drawn since the last clear; 0 == blank pad.
    const strokesRef = useRef(0);

    /** Update the stroke count, reporting empty<->drawn transitions once. */
    const setStrokes = (count: number) => {
      const was = strokesRef.current > 0;
      strokesRef.current = count;
      if (was !== count > 0) {
        onSignatureChange?.(count > 0);
      }
    };

    const getPos = (e: React.TouchEvent | React.MouseEvent) => {
      const canvas = canvasRef.current;
      if (!canvas) return { x: 0, y: 0 };
      const rect = canvas.getBoundingClientRect();
      const clientX = "touches" in e ? e.touches[0].clientX : e.clientX;
      const clientY = "touches" in e ? e.touches[0].clientY : e.clientY;
      return { x: clientX - rect.left, y: clientY - rect.top };
    };

    const startDraw = (e: React.TouchEvent | React.MouseEvent) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      drawingRef.current = true;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const pos = getPos(e);
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
    };

    const draw = (e: React.TouchEvent | React.MouseEvent) => {
      if (!drawingRef.current) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      e.preventDefault();
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const pos = getPos(e);
      ctx.lineTo(pos.x, pos.y);
      ctx.strokeStyle = "#1A1A2E";
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      ctx.stroke();
      setStrokes(strokesRef.current + 1);
    };

    const endDraw = () => {
      drawingRef.current = false;
    };

    const clear = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      setStrokes(0);
    };

    useImperativeHandle(ref, () => ({
      capture: () =>
        strokesRef.current > 0 && canvasRef.current ? canvasRef.current.toDataURL("image/png") : "",
      clear,
    }));

    return (
      <div>
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          role="img"
          aria-label="Signature capture area"
          data-testid={testId}
          style={{
            border: "1px solid #d9d9d9",
            borderRadius: 6,
            background: "#fff",
            touchAction: "none",
            display: "block",
            cursor: "crosshair",
          }}
          onMouseDown={startDraw}
          onMouseMove={draw}
          onMouseUp={endDraw}
          onMouseLeave={endDraw}
          onTouchStart={startDraw}
          onTouchMove={draw}
          onTouchEnd={endDraw}
        />
        <Space style={{ marginTop: 4 }}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {hint}
          </Text>
          <Button size="small" onClick={clear}>
            {clearLabel}
          </Button>
        </Space>
      </div>
    );
  }
);

SignaturePad.displayName = "SignaturePad";

export default SignaturePad;
