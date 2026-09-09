import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AnalyticsKpiStrip from "./AnalyticsKpiStrip";

describe("AnalyticsKpiStrip -- Strict Production & UNKNOWN != ZERO Policy", () => {
  it("renders production numbers when available", () => {
    const kpis = {
      total_pumps: 244,
      active_pumps: null,
      monitored_pumps: 211,
      pm_executed_count: 53,
      pm_done_count: 53,
      pm_scheduled_count: null,
      pm_compliance_percent: null,
      confirmed_seal_leaks: 52,
      de_leaks: 45,
      nde_leaks: 9,
      breakdown_count: 0,
      fleet_mtbf_days: null,
      fleet_mttr_hours: null,
    };

    render(<AnalyticsKpiStrip kpis={kpis} />);

    expect(screen.getByTestId("kpi-total-pumps").textContent).toContain("244");
    expect(screen.getByTestId("kpi-monitored-pumps").textContent).toContain("211");
    expect(screen.getByTestId("kpi-pm-executed").textContent).toContain("53");
    expect(screen.getByTestId("kpi-confirmed-leaks").textContent).toContain("52");
    expect(screen.getByTestId("kpi-breakdowns").textContent).toContain("0");
  });

  it("renders N/A for unpopulated/uncomputable metrics (UNKNOWN != ZERO)", () => {
    const kpis = {
      total_pumps: 244,
      active_pumps: null,
      monitored_pumps: 211,
      pm_executed_count: 53,
      pm_scheduled_count: null,
      pm_compliance_percent: null,
      confirmed_seal_leaks: 52,
      breakdown_count: 0,
      fleet_mtbf_days: null,
      fleet_mttr_hours: null,
    };

    render(<AnalyticsKpiStrip kpis={kpis} />);

    expect(screen.getByTestId("kpi-pm-compliance").textContent).toContain("N/A");
    expect(screen.getByTestId("kpi-fleet-mtbf").textContent).toContain("N/A");
    expect(screen.getByTestId("kpi-fleet-mttr").textContent).toContain("N/A");
  });
});
