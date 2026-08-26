import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PMDetailPanel from "./PMDetailPanel";

const PM = {
  id: "PM-2001",
  equipmentTag: "211-P-1A",
  area: "Boiler House",
  procedure: "Lubrication & Vibration Check",
  frequency: "MONTHLY",
  triggerType: "CALENDAR",
  checklist: ["Check oil level and condition", "Grease bearing housings"],
  lastPerformed: "2026-06-02",
  nextDue: "2026-07-24",
  assignedTechnician: "Sari Wulandari",
  estimatedDurationHours: 1.5,
  relatedWorkOrders: ["WO-1002"],
  status: "PLANNED",
  timeline: [
    { date: "2026-06-02", event: "PM performed — no anomalies found" },
    { date: "2026-06-02", event: "Next cycle scheduled for 2026-07-24" },
  ],
};

describe("PMDetailPanel", () => {
  it("renders an empty state when no PM schedule is selected", () => {
    render(<PMDetailPanel pm={null} />);

    expect(screen.getByText(/select a pm schedule/i)).toBeTruthy();
  });

  it("renders the PM Schedule Summary section", () => {
    render(<PMDetailPanel pm={PM} />);

    expect(screen.getByRole("heading", { name: "PM Schedule Summary" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Lubrication & Vibration Check" })).toBeTruthy();
    expect(screen.getByText("211-P-1A — Boiler House")).toBeTruthy();
    expect(screen.getByText("Calendar")).toBeTruthy();
    expect(screen.getByText("2026-06-02")).toBeTruthy();
    expect(screen.getByText("2026-07-24")).toBeTruthy();
    expect(screen.getByText("Sari Wulandari")).toBeTruthy();
    expect(screen.getByText("1.5 hrs")).toBeTruthy();
    expect(screen.getByText("Monthly")).toBeTruthy();
    expect(screen.getByText("Planned")).toBeTruthy();
  });

  it("renders a fallback when the PM has not yet been performed", () => {
    render(<PMDetailPanel pm={{ ...PM, lastPerformed: null }} />);

    expect(screen.getByText("Not yet performed")).toBeTruthy();
  });

  it("renders every checklist item", () => {
    render(<PMDetailPanel pm={PM} />);

    expect(screen.getByRole("heading", { name: "Checklist" })).toBeTruthy();
    expect(screen.getByText("Check oil level and condition")).toBeTruthy();
    expect(screen.getByText("Grease bearing housings")).toBeTruthy();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("renders the Related Work Orders section", () => {
    render(<PMDetailPanel pm={PM} />);

    expect(screen.getByRole("heading", { name: "Related Work Orders" })).toBeTruthy();
    expect(screen.getByText("WO-1002")).toBeTruthy();
  });

  it("renders a fallback message when there are no related work orders", () => {
    render(<PMDetailPanel pm={{ ...PM, relatedWorkOrders: [] }} />);

    expect(screen.getByText(/no related work orders/i)).toBeTruthy();
  });

  it("renders the timeline entries in order", () => {
    render(<PMDetailPanel pm={PM} />);

    expect(screen.getByRole("heading", { name: "PM Schedule Timeline" })).toBeTruthy();
    expect(screen.getByText("2026-06-02 — PM performed — no anomalies found")).toBeTruthy();
    expect(screen.getByText("2026-06-02 — Next cycle scheduled for 2026-07-24")).toBeTruthy();
  });
});
