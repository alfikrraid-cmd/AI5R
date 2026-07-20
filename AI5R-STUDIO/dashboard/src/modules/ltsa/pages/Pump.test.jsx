import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Pump from "./Pump";
import samplePumps from "../data/samplePumps";

describe("Pump workspace page", () => {
  it("renders the page header", () => {
    render(<Pump />);

    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
  });

  it("renders every sample pump in the registry table", () => {
    render(<Pump />);

    samplePumps.forEach((pump) => {
      expect(screen.getByText(pump.tag)).toBeTruthy();
    });
  });

  it("shows an empty state in the detail panel before any pump is selected", () => {
    render(<Pump />);

    expect(screen.getByText(/no pump selected/i)).toBeTruthy();
  });

  it("shows the selected pump's detail when a registry row is clicked", () => {
    render(<Pump />);

    fireEvent.click(screen.getByText("305-P-2"));

    expect(screen.getByRole("heading", { name: "Cooling Water Circulation Pump" })).toBeTruthy();
  });

  it("filters the registry table by search text", () => {
    render(<Pump />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "Amine" } });

    expect(screen.getByText("418-P-1")).toBeTruthy();
    expect(screen.queryByText("211-P-1A")).toBeNull();
  });

  it("filters the registry table by status", () => {
    render(<Pump />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "FAULT" } });

    expect(screen.getByText("641-P-5")).toBeTruthy();
    expect(screen.queryByText("211-P-1A")).toBeNull();
  });

  it("shows an empty state in the registry when no pump matches the search", () => {
    render(<Pump />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "no-such-pump-xyz" } });

    expect(screen.getByText(/no pumps match/i)).toBeTruthy();
  });
});
