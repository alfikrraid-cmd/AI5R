import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import EmptyState from "./EmptyState";

describe("EmptyState", () => {
  it("renders a title", () => {
    render(<EmptyState title="No results" />);

    expect(screen.getByText("No results")).toBeTruthy();
  });

  it("renders an optional description", () => {
    render(<EmptyState title="No results" description="Try a different filter." />);

    expect(screen.getByText("Try a different filter.")).toBeTruthy();
  });

  it("omits the description when none is given", () => {
    render(<EmptyState title="No results" />);

    expect(screen.queryByTestId("empty-state-description")).toBeNull();
  });

  it("renders inside a card-styled panel", () => {
    render(<EmptyState title="No results" />);

    expect(screen.getByTestId("panel").className).toContain("card");
  });
});
