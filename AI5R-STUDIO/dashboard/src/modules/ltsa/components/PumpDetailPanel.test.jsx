import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PumpDetailPanel from "./PumpDetailPanel";

const PUMP = {
  code: "PMP-003",
  tag: "305-P-2",
  name: "Cooling Water Circulation Pump",
  manufacturer: "Flowserve",
  type: "Vertical Turbine",
  seal: "Flowserve ISC2",
  location: "Utilities - Cooling Tower Basin",
  status: "ACTIVE",
  recommendation: "Recommended: purchase additional Type 21 seal stock.",
  knowledgeLinks: ["Seal Stock Report Q1", "Cooling Tower P&ID Rev.C"],
};

describe("PumpDetailPanel", () => {
  it("renders an empty state when no pump is selected", () => {
    render(<PumpDetailPanel pump={null} />);

    expect(screen.getByText(/select a pump/i)).toBeTruthy();
  });

  it("renders every required field for a selected pump", () => {
    render(<PumpDetailPanel pump={PUMP} />);

    expect(screen.getByText("Cooling Water Circulation Pump")).toBeTruthy();
    expect(screen.getByText("PMP-003")).toBeTruthy();
    expect(screen.getByText("Flowserve")).toBeTruthy();
    expect(screen.getByText("Vertical Turbine")).toBeTruthy();
    expect(screen.getByText("Flowserve ISC2")).toBeTruthy();
    expect(screen.getByText("Utilities - Cooling Tower Basin")).toBeTruthy();
    expect(screen.getByText("ACTIVE")).toBeTruthy();
    expect(screen.getByText(PUMP.recommendation)).toBeTruthy();
  });

  it("renders every knowledge link as a badge", () => {
    render(<PumpDetailPanel pump={PUMP} />);

    expect(screen.getByText("Seal Stock Report Q1")).toBeTruthy();
    expect(screen.getByText("Cooling Tower P&ID Rev.C")).toBeTruthy();
  });

  it("renders a fallback message when there are no knowledge links", () => {
    render(<PumpDetailPanel pump={{ ...PUMP, knowledgeLinks: [] }} />);

    expect(screen.getByText(/no knowledge links/i)).toBeTruthy();
  });
});
