import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MetricCard from "./MetricCard";

describe("MetricCard", () => {
  it("renders a title and value", () => {
    render(<MetricCard title="System" value="GREEN" />);

    expect(screen.getByText("System")).toBeTruthy();
    expect(screen.getByText("GREEN")).toBeTruthy();
  });

  it("renders inside a card-styled panel", () => {
    render(<MetricCard title="Agents" value={4} />);

    expect(screen.getByTestId("panel").className).toContain("card");
  });
});
