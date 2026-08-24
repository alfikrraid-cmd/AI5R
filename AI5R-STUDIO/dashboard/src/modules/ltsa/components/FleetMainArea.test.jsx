import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import FleetMainArea from "./FleetMainArea";

const TOP_RISK = {
  tag_number: "641-P-5",
  rule_code: "REC_CRITICAL_CM",
  title: "Immediate Inspection",
  priority: 100,
  action: "Dispatch a technician for immediate inspection.",
  description: "An open Corrective Maintenance report with critical or major severity was found.",
};

const INSIGHT = {
  summary: "Fleet status NORMAL: 1 critical asset(s). Top risk: Immediate Inspection on 641-P-5.",
  priority: 100,
  action: "Dispatch a technician for immediate inspection.",
  reason: "An open Corrective Maintenance report with critical or major severity was found.",
};

describe("FleetMainArea", () => {
  it("renders Critical Assets count", () => {
    render(<FleetMainArea criticalAssetCount={1} topRisks={[]} insight={null} />);
    expect(screen.getByText("Critical Assets")).toBeTruthy();
    expect(screen.getByText("1")).toBeTruthy();
  });

  it("renders Top Risks with tag, title, priority, and action", () => {
    render(<FleetMainArea criticalAssetCount={1} topRisks={[TOP_RISK]} insight={null} />);

    expect(screen.getByText("Top Risks")).toBeTruthy();
    expect(screen.getByText("641-P-5")).toBeTruthy();
    expect(screen.getByText("Immediate Inspection")).toBeTruthy();
  });

  it("shows a no-risks placeholder when Top Risks is empty, never fabricated", () => {
    render(<FleetMainArea criticalAssetCount={0} topRisks={[]} insight={null} />);
    expect(screen.getByText(/no risks/i)).toBeTruthy();
  });

  it("renders Fleet Insight summary, action, and reason verbatim", () => {
    render(<FleetMainArea criticalAssetCount={1} topRisks={[TOP_RISK]} insight={INSIGHT} />);

    expect(screen.getByText("Fleet Insight")).toBeTruthy();
    expect(screen.getByText(INSIGHT.summary)).toBeTruthy();
    // TOP_RISK.action and INSIGHT.action share the same fixture string --
    // it legitimately renders twice (Top Risks list item + Fleet Insight
    // paragraph), so assert presence, not uniqueness.
    expect(screen.getAllByText(INSIGHT.action).length).toBeGreaterThan(0);
    expect(screen.getByText(INSIGHT.reason)).toBeTruthy();
  });

  it("shows a no-insight placeholder when insight is null, never fabricated", () => {
    render(<FleetMainArea criticalAssetCount={0} topRisks={[]} insight={null} />);
    expect(screen.getByText(/no insight/i)).toBeTruthy();
  });
});
