import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import FleetHero from "./FleetHero";

describe("FleetHero", () => {
  it("renders Fleet Health Score and Fleet Status", () => {
    render(<FleetHero healthScore={86.5} status="NORMAL" />);

    expect(screen.getByText("Fleet Health Score")).toBeTruthy();
    expect(screen.getByText("87")).toBeTruthy();
    expect(screen.getByText("Fleet Status")).toBeTruthy();
    expect(screen.getByText("NORMAL")).toBeTruthy();
  });

  it("shows Unavailable for a null health score, never a fabricated number", () => {
    render(<FleetHero healthScore={null} status="UNKNOWN" />);

    expect(screen.getByText("Unavailable")).toBeTruthy();
  });
});
