import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MaintenanceEventDetailPanel from "./MaintenanceEventDetailPanel";

const PM_EVENT = {
  id: "PM-2008",
  type: "PM",
  date: "2025-12-10",
  title: "Seal Chamber Condition Check",
  status: "OVERDUE",
  assignedTechnician: "Dedi Kurniawan",
  raw: {
    frequency: "RUNTIME_BASED",
    triggerType: "METER",
    estimatedDurationHours: 2,
    checklist: ["Inspect seal chamber for leakage", "Check seal flush pressure"],
  },
};

const CM_EVENT = {
  id: "CM-3001",
  type: "CM",
  date: "2026-07-18",
  title: "Third mechanical seal failure in 90 days.",
  status: "IN_PROGRESS",
  assignedTechnician: "Dedi Kurniawan",
  raw: {
    failureCategory: "SEAL_FAILURE",
    severity: "CRITICAL",
    priority: "CRITICAL",
    rootCause: "Seal flush plan 52 pressure below minimum.",
    immediateAction: "Pump shut down and isolated.",
    correctiveAction: "Replace mechanical seal.",
    downtimeHours: 18,
  },
};

const WO_EVENT = {
  id: "WO-1001",
  type: "WO",
  date: "2026-07-18",
  title: "Seal replacement — repeat failures",
  status: "OPEN",
  assignedTechnician: "Dedi Kurniawan",
  raw: {
    workType: "CM",
    requestedBy: "Operations - SWS",
    dueDate: "2026-07-21",
    priority: "CRITICAL",
    description: "Third seal failure in 90 days on the SWS bottoms pump.",
  },
};

describe("MaintenanceEventDetailPanel", () => {
  it("renders an empty state when no event is selected", () => {
    render(<MaintenanceEventDetailPanel event={null} />);

    expect(screen.getByText(/select an event/i)).toBeTruthy();
  });

  it("renders PM-specific details for a PM event", () => {
    render(<MaintenanceEventDetailPanel event={PM_EVENT} />);

    expect(screen.getByRole("heading", { name: "Event Summary" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Preventive Maintenance Details" })).toBeTruthy();
    expect(screen.getByText("Runtime-based")).toBeTruthy();
    expect(screen.getByText("Runtime Meter")).toBeTruthy();
    expect(screen.getByText("Inspect seal chamber for leakage")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Corrective Maintenance Details" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Work Order Details" })).toBeNull();
  });

  it("renders CM-specific details for a CM event", () => {
    render(<MaintenanceEventDetailPanel event={CM_EVENT} />);

    expect(screen.getByRole("heading", { name: "Corrective Maintenance Details" })).toBeTruthy();
    expect(screen.getByText("Seal Failure")).toBeTruthy();
    expect(screen.getByText("Seal flush plan 52 pressure below minimum.")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Preventive Maintenance Details" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Work Order Details" })).toBeNull();
  });

  it("renders WO-specific details for a Work Order event", () => {
    render(<MaintenanceEventDetailPanel event={WO_EVENT} />);

    expect(screen.getByRole("heading", { name: "Work Order Details" })).toBeTruthy();
    expect(screen.getByText("Operations - SWS")).toBeTruthy();
    expect(screen.getByText("Third seal failure in 90 days on the SWS bottoms pump.")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Preventive Maintenance Details" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Corrective Maintenance Details" })).toBeNull();
  });
});
