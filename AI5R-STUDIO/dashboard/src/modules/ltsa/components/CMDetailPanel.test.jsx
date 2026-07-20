import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import CMDetailPanel from "./CMDetailPanel";

const CM = {
  id: "CM-3001",
  equipmentTag: "641-P-5",
  area: "SWS Unit",
  failureCategory: "SEAL_FAILURE",
  severity: "CRITICAL",
  priority: "HIGH",
  failureDescription: "Third mechanical seal failure in 90 days.",
  rootCause: "Seal flush plan 52 pressure below minimum.",
  immediateAction: "Pump shut down and isolated.",
  correctiveAction: "Replace mechanical seal and inspect flush plan piping.",
  downtimeHours: 18,
  assignedTechnician: "Dedi Kurniawan",
  relatedPump: "641-P-5",
  relatedWorkOrder: "WO-1001",
  status: "IN_PROGRESS",
  timeline: [
    { date: "2026-07-18", event: "Failure reported by operations" },
    { date: "2026-07-18", event: "Pump isolated, standby placed in service" },
  ],
};

describe("CMDetailPanel", () => {
  it("renders an empty state when no report is selected", () => {
    render(<CMDetailPanel cm={null} />);

    expect(screen.getByText(/select a report/i)).toBeTruthy();
  });

  it("renders the Corrective Maintenance Summary section", () => {
    render(<CMDetailPanel cm={CM} />);

    expect(screen.getByRole("heading", { name: "Corrective Maintenance Summary" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Third mechanical seal failure in 90 days." })).toBeTruthy();
    expect(screen.getByText("641-P-5 — SWS Unit")).toBeTruthy();
    expect(screen.getByText("Dedi Kurniawan")).toBeTruthy();
    expect(screen.getByText("18 hrs")).toBeTruthy();
    expect(screen.getByText("Seal Failure")).toBeTruthy();
    expect(screen.getByText("CRITICAL")).toBeTruthy();
    expect(screen.getByText("IN_PROGRESS")).toBeTruthy();
  });

  it("renders the Root Cause & Actions section", () => {
    render(<CMDetailPanel cm={CM} />);

    expect(screen.getByRole("heading", { name: "Root Cause & Actions" })).toBeTruthy();
    expect(screen.getByText(CM.rootCause)).toBeTruthy();
    expect(screen.getByText(CM.immediateAction)).toBeTruthy();
    expect(screen.getByText(CM.correctiveAction)).toBeTruthy();
  });

  it("renders the Related Records section with related pump and work order", () => {
    render(<CMDetailPanel cm={CM} />);

    expect(screen.getByRole("heading", { name: "Related Records" })).toBeTruthy();
    expect(screen.getByText("641-P-5")).toBeTruthy();
    expect(screen.getByText("WO-1001")).toBeTruthy();
  });

  it("renders fallback messages when there is no related pump or work order", () => {
    render(<CMDetailPanel cm={{ ...CM, relatedPump: null, relatedWorkOrder: null }} />);

    expect(screen.getByText(/no related pump/i)).toBeTruthy();
    expect(screen.getByText(/no related work order/i)).toBeTruthy();
  });

  it("renders the timeline entries in order", () => {
    render(<CMDetailPanel cm={CM} />);

    expect(screen.getByRole("heading", { name: "Corrective Maintenance Timeline" })).toBeTruthy();
    expect(screen.getByText("2026-07-18 — Failure reported by operations")).toBeTruthy();
    expect(screen.getByText("2026-07-18 — Pump isolated, standby placed in service")).toBeTruthy();
  });
});
