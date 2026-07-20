import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PumpDetailPanel from "./PumpDetailPanel";

const PUMP = {
  code: "PMP-003",
  tag: "305-P-2",
  name: "Cooling Water Circulation Pump",
  manufacturer: "Flowserve",
  type: "Vertical Turbine",
  seal: "Flowserve ISC2",
  location: "Utilities - Cooling Tower Basin",
  area: "Utilities",
  status: "RUNNING",
  healthScore: 74,
  availability: 96.8,
  runtimeHours: 31450,
  lastPM: "2026-02-20",
  nextPM: "2026-08-20",
  openWO: 1,
  criticality: "MEDIUM",
  recommendation: "Recommended: purchase additional Type 21 seal stock.",
  knowledgeLinks: ["Seal Stock Report Q1", "Cooling Tower P&ID Rev.C"],
};

describe("PumpDetailPanel", () => {
  it("renders an empty state when no pump is selected", () => {
    render(<PumpDetailPanel pump={null} />);

    expect(screen.getByText(/select a pump/i)).toBeTruthy();
  });

  it("renders the Equipment Summary section", () => {
    render(<PumpDetailPanel pump={PUMP} />);

    expect(screen.getByRole("heading", { name: "Equipment Summary" })).toBeTruthy();
    expect(screen.getByText("Cooling Water Circulation Pump")).toBeTruthy();
    expect(screen.getByText("PMP-003")).toBeTruthy();
    expect(screen.getByText("305-P-2")).toBeTruthy();
    expect(screen.getByText("Flowserve")).toBeTruthy();
    expect(screen.getByText("Vertical Turbine")).toBeTruthy();
    expect(screen.getByText("Flowserve ISC2")).toBeTruthy();
    expect(screen.getByText("Utilities - Cooling Tower Basin")).toBeTruthy();
    expect(screen.getByText("Utilities")).toBeTruthy();
    expect(screen.getByText("MEDIUM")).toBeTruthy();
    expect(screen.getByText("RUNNING")).toBeTruthy();
  });

  it("renders the Maintenance Summary section", () => {
    render(<PumpDetailPanel pump={PUMP} />);

    expect(screen.getByRole("heading", { name: "Maintenance Summary" })).toBeTruthy();
    expect(screen.getByText("74")).toBeTruthy();
    expect(screen.getByText("96.8%")).toBeTruthy();
    expect(screen.getByText("31,450 hrs")).toBeTruthy();
    expect(screen.getByText("2026-02-20")).toBeTruthy();
    expect(screen.getByText("2026-08-20")).toBeTruthy();
    expect(screen.getByText("1")).toBeTruthy();
  });

  it("renders the AI Recommendation section with knowledge links", () => {
    render(<PumpDetailPanel pump={PUMP} />);

    expect(screen.getByRole("heading", { name: "AI Recommendation" })).toBeTruthy();
    expect(screen.getByText(PUMP.recommendation)).toBeTruthy();
    expect(screen.getByText("Seal Stock Report Q1")).toBeTruthy();
    expect(screen.getByText("Cooling Tower P&ID Rev.C")).toBeTruthy();
  });

  it("renders a fallback message when there are no knowledge links", () => {
    render(<PumpDetailPanel pump={{ ...PUMP, knowledgeLinks: [] }} />);

    expect(screen.getByText(/no knowledge links/i)).toBeTruthy();
  });

  it("renders the Quick Actions section with View History and Documents disabled", () => {
    render(<PumpDetailPanel pump={PUMP} />);

    expect(screen.getByRole("heading", { name: "Quick Actions" })).toBeTruthy();

    ["View History", "Documents"].forEach((label) => {
      const button = screen.getByRole("button", { name: label });
      expect(button).toBeTruthy();
      expect(button.disabled).toBe(true);
    });
  });

  it("calls onCreatePM when the Create PM quick action is clicked", () => {
    const onCreatePM = vi.fn();
    render(<PumpDetailPanel pump={PUMP} onCreatePM={onCreatePM} onCreateCM={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Create PM" }));

    expect(onCreatePM).toHaveBeenCalledTimes(1);
  });

  it("calls onCreateCM when the Create CM quick action is clicked", () => {
    const onCreateCM = vi.fn();
    render(<PumpDetailPanel pump={PUMP} onCreatePM={() => {}} onCreateCM={onCreateCM} />);

    fireEvent.click(screen.getByRole("button", { name: "Create CM" }));

    expect(onCreateCM).toHaveBeenCalledTimes(1);
  });
});
