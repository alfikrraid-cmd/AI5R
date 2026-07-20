import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import WorkOrderDetailPanel from "./WorkOrderDetailPanel";

const WORK_ORDER = {
  id: "WO-1001",
  title: "Seal replacement — repeat failures",
  equipmentTag: "641-P-5",
  area: "SWS Unit",
  workType: "CM",
  status: "OPEN",
  priority: "CRITICAL",
  assignedTo: "Dedi Kurniawan",
  requestedBy: "Operations - SWS",
  createdDate: "2026-07-18",
  dueDate: "2026-07-21",
  description: "Third seal failure in 90 days. Shutdown for seal replacement.",
  timeline: [
    { date: "2026-07-18", event: "Work order created from AI Recommendation" },
    { date: "2026-07-19", event: "Parts requisition submitted" },
  ],
};

describe("WorkOrderDetailPanel", () => {
  it("renders an empty state when no work order is selected", () => {
    render(<WorkOrderDetailPanel workOrder={null} />);

    expect(screen.getByText(/select a work order/i)).toBeTruthy();
  });

  it("renders the Work Order Summary section", () => {
    render(<WorkOrderDetailPanel workOrder={WORK_ORDER} />);

    expect(screen.getByRole("heading", { name: "Work Order Summary" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: WORK_ORDER.title })).toBeTruthy();
    expect(screen.getByText("WO-1001")).toBeTruthy();
    expect(screen.getByText("641-P-5")).toBeTruthy();
    expect(screen.getByText("SWS Unit")).toBeTruthy();
    expect(screen.getByText("CM")).toBeTruthy();
    expect(screen.getByText("Dedi Kurniawan")).toBeTruthy();
    expect(screen.getByText("Operations - SWS")).toBeTruthy();
    expect(screen.getByText("2026-07-18")).toBeTruthy();
    expect(screen.getByText("2026-07-21")).toBeTruthy();
    expect(screen.getByText("CRITICAL")).toBeTruthy();
    expect(screen.getByText("OPEN")).toBeTruthy();
  });

  it("renders the Description section", () => {
    render(<WorkOrderDetailPanel workOrder={WORK_ORDER} />);

    expect(screen.getByRole("heading", { name: "Description" })).toBeTruthy();
    expect(screen.getByText(WORK_ORDER.description)).toBeTruthy();
  });

  it("renders the timeline entries in order", () => {
    render(<WorkOrderDetailPanel workOrder={WORK_ORDER} />);

    expect(screen.getByRole("heading", { name: "Work Order Timeline" })).toBeTruthy();
    expect(
      screen.getByText("2026-07-18 — Work order created from AI Recommendation")
    ).toBeTruthy();
    expect(screen.getByText("2026-07-19 — Parts requisition submitted")).toBeTruthy();
  });
});
