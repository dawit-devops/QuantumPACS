import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import { MetricsSkeleton } from "../metrics/MetricsSkeleton";

describe("MetricsSkeleton", () => {
  it("renders stat card placeholders", () => {
    renderWithApp(<MetricsSkeleton />);
    const cards = document.querySelectorAll(".ant-skeleton-input");
    expect(cards.length).toBeGreaterThanOrEqual(3);
  });

  it("renders chart area placeholders", () => {
    renderWithApp(<MetricsSkeleton />);
    const paragraphs = document.querySelectorAll(".ant-skeleton-paragraph");
    expect(paragraphs.length).toBeGreaterThanOrEqual(1);
  });

  it("renders data-testid for loading detection", () => {
    renderWithApp(<MetricsSkeleton />);
    expect(screen.getByTestId("metrics-skeleton")).toBeInTheDocument();
  });
});
