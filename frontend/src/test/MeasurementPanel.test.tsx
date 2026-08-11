import { describe, it, expect } from "vitest";
import { parseAnnotations } from "../detail/MeasurementPanel";

describe("parseAnnotations", () => {
  it("maps a CobbAngleTool annotation with stats.angle to degrees", () => {
    const image =
      "wadors:https://pacs.example.com/dicomweb/studies/1/instances/2";
    const annotations = [
      {
        annotationUID: "cobb-1",
        metadata: { toolName: "CobbAngleTool" },
        data: {
          label: "",
          cachedStats: { [image]: { angle: 42.3 } },
        },
      },
    ];

    const result = parseAnnotations(annotations, image);
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      annotationUID: "cobb-1",
      toolName: "CobbAngle",
      type: "CobbAngle",
      value: "42.3°",
    });
  });

  it("maps a ProbeTool annotation with stats.value and modalityUnit", () => {
    const image =
      "wadors:https://pacs.example.com/dicomweb/studies/1/instances/2";
    const annotations = [
      {
        annotationUID: "probe-1",
        metadata: { toolName: "ProbeTool" },
        data: {
          cachedStats: { [image]: { value: -523, modalityUnit: "HU" } },
        },
      },
    ];

    const result = parseAnnotations(annotations, image);
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      annotationUID: "probe-1",
      toolName: "Probe",
      type: "Probe",
      value: "-523.0 HU",
    });
  });

  it("joins multi-value probe stats (ECG/US) with a separator", () => {
    const image =
      "wadors:https://pacs.example.com/dicomweb/studies/1/instances/2";
    const annotations = [
      {
        annotationUID: "probe-2",
        metadata: { toolName: "ProbeTool" },
        data: {
          cachedStats: {
            [image]: { value: [1.25, 2.5], modalityUnit: "mV" },
          },
        },
      },
    ];

    const result = parseAnnotations(annotations, image);
    expect(result[0]?.value).toBe("1.3 / 2.5 mV");
  });

  it("maps a CircleROITool annotation with area and mean", () => {
    const image =
      "wadors:https://pacs.example.com/dicomweb/studies/1/instances/2";
    const annotations = [
      {
        annotationUID: "circle-1",
        metadata: { toolName: "CircleROITool" },
        data: {
          cachedStats: { [image]: { area: 78.5, mean: 120 } },
        },
      },
    ];

    const result = parseAnnotations(annotations, image);
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      annotationUID: "circle-1",
      toolName: "CircleROI",
      type: "CircleROI",
      value: "78.5 mm² μ=120.0",
    });
  });

  it("skips a CobbAngleTool annotation without cached stats", () => {
    const image =
      "wadors:https://pacs.example.com/dicomweb/studies/1/instances/2";
    const annotations = [
      {
        annotationUID: "cobb-incomplete",
        metadata: { toolName: "CobbAngleTool" },
        data: {},
      },
    ];

    const result = parseAnnotations(annotations, image);
    expect(result).toHaveLength(0);
  });

  it("omits the unit suffix when stats have no modalityUnit", () => {
    const image =
      "wadors:https://pacs.example.com/dicomweb/studies/1/instances/2";
    const annotations = [
      {
        annotationUID: "probe-3",
        metadata: { toolName: "ProbeTool" },
        data: {
          cachedStats: { [image]: { value: 128 } },
        },
      },
    ];

    const result = parseAnnotations(annotations, image);
    expect(result[0]?.value).toBe("128.0");
  });

  it("skips a ProbeTool annotation without a value", () => {
    const image =
      "wadors:https://pacs.example.com/dicomweb/studies/1/instances/2";
    const annotations = [
      {
        annotationUID: "probe-incomplete",
        metadata: { toolName: "ProbeTool" },
        data: { cachedStats: { [image]: { value: null } } },
      },
    ];

    const result = parseAnnotations(annotations, image);
    expect(result).toHaveLength(0);
  });
});
