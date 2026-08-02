import React from "react";
import { render, screen } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import { MemoryRouter } from "react-router";
import { describe, it, expect } from "vitest";
import NotFound from "../notfound/NotFound";

describe("NotFound", () => {
  it("renders without crashing", () => {
    renderWithApp(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>,
    );
  });

  it("renders heading", () => {
    renderWithApp(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>,
    );
    expect(screen.getByText("Oops! Page not found")).toBeInTheDocument();
  });

  it("renders link to home page", () => {
    renderWithApp(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>,
    );
    const link = screen.getByRole("link", { name: /Go to home page/ });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/");
  });
});
