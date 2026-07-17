import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Pump from "./Pump";
import samplePumps from "../data/samplePumps";

describe("Pump workspace page", () => {
  it("renders the page header", () => {
    render(<Pump />);

    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
  });

  it("renders all 10 sample pumps in the registry table", () => {
    render(<Pump />);

    samplePumps.forEach((pump) => {
      expect(screen.getByText(pump.code)).toBeTruthy();
    });
  });

  it("shows an empty state in the detail panel before any pump is selected", () => {
    render(<Pump />);

    expect(screen.getByText(/no pump selected/i)).toBeTruthy();
  });

  it("shows the selected pump's detail when a registry row is clicked", () => {
    render(<Pump />);

    fireEvent.click(screen.getByText("PMP-003"));

    expect(screen.getByRole("heading", { name: "Cooling Water Circulation Pump" })).toBeTruthy();
  });

  it("filters the registry table by search text", () => {
    render(<Pump />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "Amine" } });

    expect(screen.getByText("PMP-006")).toBeTruthy();
    expect(screen.queryByText("PMP-001")).toBeNull();
  });

  it("filters the registry table by status", () => {
    render(<Pump />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "FAULT" } });

    expect(screen.getByText("PMP-009")).toBeTruthy();
    expect(screen.queryByText("PMP-001")).toBeNull();
  });
});
