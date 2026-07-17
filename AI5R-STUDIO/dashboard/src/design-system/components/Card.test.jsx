import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Card from "./Card";

describe("Card", () => {
  it("renders a title heading and children", () => {
    render(<Card title="Digital Employees">content</Card>);

    expect(screen.getByRole("heading", { name: "Digital Employees" })).toBeTruthy();
    expect(screen.getByText("content")).toBeTruthy();
  });

  it("renders without a title", () => {
    render(<Card>content only</Card>);

    expect(screen.queryAllByRole("heading").length).toBe(0);
    expect(screen.getByText("content only")).toBeTruthy();
  });

  it("is a card-styled panel (composition, not a duplicate implementation)", () => {
    render(<Card title="X">y</Card>);

    expect(screen.getByTestId("panel").className).toContain("card");
  });
});
