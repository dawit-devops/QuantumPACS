import React from "react";
import { render, screen } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import { describe, it, expect } from "vitest";
import QuantumLogo from "../common/QuantumLogo";

describe("QuantumLogo", () => {
  it("renders without crashing", () => {
    renderWithApp(<QuantumLogo />);
  });

  it("renders SVG element", () => {
    renderWithApp(<QuantumLogo />);
    const svg = document.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("renders text when showText is true (default)", () => {
    renderWithApp(<QuantumLogo />);
    const svg = document.querySelector("svg");
    expect(svg?.textContent).toContain("Quantum");
    expect(screen.getByText("PACS")).toBeInTheDocument();
  });

  it("does not render text when showText is false", () => {
    renderWithApp(<QuantumLogo showText={false} />);
    expect(screen.queryByText("PACS")).not.toBeInTheDocument();
    const svg = document.querySelector("svg");
    expect(svg?.textContent).not.toContain("Quantum");
  });

  it("accepts size prop", () => {
    renderWithApp(<QuantumLogo size={60} />);
    const svg = document.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });
});
