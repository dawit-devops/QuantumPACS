import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "antd";
import { EmptyState, renderEmpty } from "../common/EmptyState";

describe("EmptyState", () => {
  it("renders default empty message", () => {
    const { container } = render(<EmptyState />);
    expect(container.querySelector(".ant-empty-description")).toHaveTextContent(
      "No data",
    );
  });

  it("renders custom description", () => {
    render(<EmptyState description="No files found" />);
    expect(screen.getByText("No files found")).toBeInTheDocument();
  });

  it("renders with action button", () => {
    render(
      <EmptyState
        description="No users yet"
        action={<Button>Add User</Button>}
      />,
    );
    expect(screen.getByText("No users yet")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Add User" }),
    ).toBeInTheDocument();
  });
});

describe("renderEmpty", () => {
  it("returns a ReactNode with default message", () => {
    const { container } = render(<>{renderEmpty()}</>);
    expect(container.querySelector(".ant-empty-description")).toHaveTextContent(
      "No data",
    );
  });
});
