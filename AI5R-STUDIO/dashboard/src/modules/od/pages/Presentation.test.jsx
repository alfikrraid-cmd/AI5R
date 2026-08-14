import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Presentation from "./Presentation";

const blueprint = {
  blueprintId: "BLUEPRINT-1",
  businessIdentity: "Acme Pump Services",
  objective: "no more missed service calls",
  context: "help me run my business",
  capturedAt: "2026-07-21T00:00:00.000Z",
};

describe("Presentation page", () => {
  it("shows an empty state when no blueprint has been sealed yet", () => {
    render(<Presentation blueprint={null} />);

    expect(screen.getByText("No Business Blueprint yet")).toBeTruthy();
  });

  it("renders the sealed blueprint read-only", () => {
    render(<Presentation blueprint={blueprint} />);

    expect(screen.getByRole("heading", { name: "Acme Pump Services" })).toBeTruthy();
    expect(screen.getByText("Sealed")).toBeTruthy();
    expect(screen.getByText("no more missed service calls")).toBeTruthy();
    expect(screen.getByText("help me run my business")).toBeTruthy();
    expect(screen.getByText(/BLUEPRINT-1/)).toBeTruthy();
  });
});
