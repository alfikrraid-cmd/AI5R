import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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

  it("opens the Create PM Schedule dialog from the selected pump's Quick Actions", () => {
    render(<Pump />);

    fireEvent.click(screen.getByText("305-P-2"));
    fireEvent.click(screen.getByRole("button", { name: "Create PM" }));

    expect(screen.getByRole("heading", { name: "Create PM Schedule" })).toBeTruthy();
  });

  it("opens the Create CM Report dialog from the selected pump's Quick Actions", () => {
    render(<Pump />);

    fireEvent.click(screen.getByText("305-P-2"));
    fireEvent.click(screen.getByRole("button", { name: "Create CM" }));

    expect(screen.getByRole("heading", { name: "Create CM Report" })).toBeTruthy();
  });

  it("navigates to Maintenance History when View History is clicked from Quick Actions", () => {
    const onNavigate = vi.fn();
    render(<Pump onNavigate={onNavigate} />);

    fireEvent.click(screen.getByText("305-P-2"));
    fireEvent.click(screen.getByRole("button", { name: "View History" }));

    expect(onNavigate).toHaveBeenCalledWith("history");
  });
});
