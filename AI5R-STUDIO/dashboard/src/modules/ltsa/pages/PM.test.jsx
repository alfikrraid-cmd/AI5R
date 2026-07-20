import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PM from "./PM";
import samplePMSchedules from "../data/samplePMSchedules";

describe("Preventive Maintenance workspace page", () => {
  it("renders the page header", () => {
    render(<PM />);

    expect(screen.getByRole("heading", { name: "Preventive Maintenance Workspace" })).toBeTruthy();
  });

  it("renders every sample PM schedule in the list", () => {
    render(<PM />);

    samplePMSchedules.forEach((pm) => {
      expect(screen.getByText(pm.id)).toBeTruthy();
    });
  });

  it("shows an empty state in the detail panel before any PM schedule is selected", () => {
    render(<PM />);

    expect(screen.getByText(/no pm schedule selected/i)).toBeTruthy();
  });

  it("shows the selected PM schedule's detail when a list row is clicked", () => {
    render(<PM />);

    fireEvent.click(screen.getByText("PM-2004"));

    expect(screen.getByRole("heading", { name: "Wear-Plate Inspection" })).toBeTruthy();
  });

  it("filters the list by search text", () => {
    render(<PM />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "walkdown" } });

    expect(screen.getByText("PM-2006")).toBeTruthy();
    expect(screen.queryByText("PM-2001")).toBeNull();
  });

  it("filters the list by status", () => {
    render(<PM />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "OVERDUE" } });

    expect(screen.getByText("PM-2002")).toBeTruthy();
    expect(screen.getByText("PM-2003")).toBeTruthy();
    expect(screen.getByText("PM-2008")).toBeTruthy();
    expect(screen.queryByText("PM-2001")).toBeNull();
  });

  it("shows an empty state in the list when no PM schedule matches the search", () => {
    render(<PM />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "no-such-pm-xyz" } });

    expect(screen.getByText(/no pm schedules match/i)).toBeTruthy();
  });

  it("opens the Create PM Schedule modal when the header action is clicked", () => {
    render(<PM />);

    fireEvent.click(screen.getByRole("button", { name: "+ Create PM Schedule" }));

    expect(screen.getByRole("heading", { name: "Create PM Schedule" })).toBeTruthy();
  });

  it("creates a new PM schedule via the modal, closes it, and selects the new entry", () => {
    render(<PM />);

    fireEvent.click(screen.getByRole("button", { name: "+ Create PM Schedule" }));
    fireEvent.change(screen.getByLabelText("Equipment"), { target: { value: "533-P-1" } });

    fireEvent.click(screen.getByRole("button", { name: "Create PM Schedule" }));

    expect(screen.queryByRole("heading", { name: "Create PM Schedule" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Standard Lubrication" })).toBeTruthy();
    expect(screen.getByText("PM-2009")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("PM-2009 created.");
  });
});
