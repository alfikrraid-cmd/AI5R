import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StatusBadge from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders the label and status", () => {
    render(<StatusBadge label="Brain" status="ACTIVE" />);

    expect(screen.getByText("Brain")).toBeTruthy();
    expect(screen.getByText("ACTIVE")).toBeTruthy();
  });

  it("applies a status-derived modifier class", () => {
    render(<StatusBadge label="Brain" status="ACTIVE" />);

    expect(screen.getByTestId("status-badge").className).toContain("ds-status-badge--active");
  });

  it("falls back to a neutral modifier for unknown status", () => {
    render(<StatusBadge label="Brain" status="WEIRD" />);

    expect(screen.getByTestId("status-badge").className).toContain("ds-status-badge--neutral");
  });
});
