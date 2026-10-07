import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import BadActorsTable from "./BadActorsTable";
import HistoricalFindingsFeed from "./HistoricalFindingsFeed";
import DomainAnalyticsTabs from "./DomainAnalyticsTabs";
import LtsaGlobalFilterBar from "./LtsaGlobalFilterBar";

vi.mock("../../../api/ai5rClient", () => ({
  getLtsaAnalyticsFilters: vi.fn().mockResolvedValue({
    areas: [{ area: "HCC", pump_count: 82 }, { area: "HOC", pump_count: 54 }],
    pumps: [{ tag_number: "220-P-3A", area: "HOC", pump_type: "BB" }],
    date_range: { min_date: "2026-07-01", max_date: "2026-07-31" },
  }),
}));

describe("BadActorsTable Component", () => {
  it("renders table of repeat bad actor pumps and handles drill-down", () => {
    const badActors = [
      {
        pump_tag: "220-P-3A",
        area: "HOC",
        pump_type: "BB",
        api_plan: "22/62",
        leak_count: 3,
        cmon_readings: 3,
        pm_count: 0,
        latest_leak_date: "2026-07-21",
      },
    ];
    const onNavigate = vi.fn();
    render(<BadActorsTable badActors={badActors} onNavigate={onNavigate} />);

    expect(screen.getByTestId("bad-actors-table")).toBeTruthy();
    expect(screen.getByText("220-P-3A")).toBeTruthy();
    expect(screen.getByText("HOC")).toBeTruthy();

    fireEvent.click(screen.getByText("220-P-3A"));
    expect(onNavigate).toHaveBeenCalledWith("history", { assetTag: "220-P-3A" });

    fireEvent.click(screen.getByRole("button", { name: /inspect 360/i }));
    expect(onNavigate).toHaveBeenCalledWith("history", { assetTag: "220-P-3A" });
  });

  it("handles empty bad actors gracefully", () => {
    render(<BadActorsTable badActors={[]} />);
    expect(screen.getByText(/no repeat bad actor pumps found/i)).toBeTruthy();
  });
});

describe("HistoricalFindingsFeed Component", () => {
  it("renders verified engineering observations and handles drill-down", () => {
    const findings = [
      {
        pump_tag: "140-P-16A",
        remarks: "STANDBY, bocor dari draingland 1/2 detik",
        api_plan: "32/61",
        pump_type: "OH",
        leak_de: true,
        leak_nde: null,
        detected_date: "2026-07-30",
      },
    ];
    const onNavigate = vi.fn();
    render(<HistoricalFindingsFeed findings={findings} onNavigate={onNavigate} />);

    expect(screen.getByTestId("historical-findings-feed")).toBeTruthy();
    expect(screen.getByText("140-P-16A")).toBeTruthy();
    expect(screen.getByText(/STANDBY, bocor dari draingland 1\/2 detik/i)).toBeTruthy();
    expect(screen.getByText("LEAK OBSERVATION")).toBeTruthy();

    fireEvent.click(screen.getByText("140-P-16A"));
    expect(onNavigate).toHaveBeenCalledWith("history", { assetTag: "140-P-16A" });
  });

  it("handles empty findings gracefully", () => {
    render(<HistoricalFindingsFeed findings={[]} />);
    expect(screen.getByText(/no field leak findings recorded/i)).toBeTruthy();
  });
});

describe("DomainAnalyticsTabs Component", () => {
  const sealAnalytics = {
    summary: {
      seal_installations_count: null,
      total_registered_seals: null,
      total_stock_units: null,
      fleet_inventory_available: false,
      has_installation_data: false,
    },
    leaks_by_pump_type: [{ pump_type: "BB", leak_count: 22 }],
    leaks_by_api_plan: [{ api_plan: "11/61", leak_count: 12 }],
  };

  const materialAnalytics = {
    has_data: false,
    message: "Internal component consumption, rebuild kits, and spare parts tracking data have not been ingested for the current contract period.",
  };

  const effectivenessAnalytics = {
    metrics: {
      pm_executed: 53,
      confirmed_leaks: 52,
      pm_to_leak_ratio: 1.02,
      proactive_ratio_percent: 50.5,
      first_time_fix_rate: null,
      mean_time_to_respond_days: null,
    },
    area_effectiveness: [
      { area: "HCC", pm_count: 19, leak_count: 22, proactive_percent: 46.3 },
    ],
  };

  it("switches tabs and renders strict UNKNOWN != ZERO policy in material consumption", () => {
    render(
      <DomainAnalyticsTabs
        sealAnalytics={sealAnalytics}
        materialAnalytics={materialAnalytics}
        effectivenessAnalytics={effectivenessAnalytics}
        kpis={{ de_leaks: 45, nde_leaks: 9 }}
      />
    );

    // Initial tab: Seals
    expect(screen.getByTestId("tab-content-seals")).toBeTruthy();
    // LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B -- installations, never
    // "replacements"; fleet-wide registry/stock hidden for a scoped view.
    expect(screen.getByText("SEAL INSTALLATIONS")).toBeTruthy();
    expect(screen.getByText(/no recorded installation events in scope/i)).toBeTruthy();
    expect(screen.queryByText(/replacement/i)).toBeNull();
    expect(screen.queryByTestId("seal-fleet-inventory-card")).toBeNull();

    // Switch to Materials
    fireEvent.click(screen.getByRole("button", { name: /material consumption/i }));
    expect(screen.getByTestId("tab-content-materials")).toBeTruthy();
    expect(screen.getByText(/Strict Production Policy: UNKNOWN ≠ ZERO/i)).toBeTruthy();

    // Switch to Effectiveness
    fireEvent.click(screen.getByRole("button", { name: /maintenance effectiveness/i }));
    expect(screen.getByTestId("tab-content-effectiveness")).toBeTruthy();
    expect(screen.getByText("50.5%")).toBeTruthy();
    expect(screen.getByText("1.02")).toBeTruthy();
  });
});

describe("LtsaGlobalFilterBar Component", () => {
  const authorizedAreas = [
    { code: "HOC", label: "HOC" },
    { code: "HSC", label: "HSC" },
    { code: "S_PAKNING", label: "S. Pakning" },
  ];
  const filterOptions = {
    pumps: [
      { tag_number: "110-P-1", area: "HOC", canonical_area: "HOC", pump_type: "OH" },
      { tag_number: "SPK-P-1", area: "SPK", canonical_area: "S_PAKNING", pump_type: "BB" },
    ],
    date_range: { min_date: "2026-07-01", max_date: "2026-07-31" },
  };

  it("offers All Areas plus only the backend's authorized areas and reports area changes", () => {
    const onAreaChange = vi.fn();
    const onFilterChange = vi.fn();
    render(
      <LtsaGlobalFilterBar
        authorizedAreas={authorizedAreas}
        filterOptions={filterOptions}
        onAreaChange={onAreaChange}
        onFilterChange={onFilterChange}
      />
    );

    const select = screen.getByLabelText("Filter by Area");
    const options = Array.from(select.querySelectorAll("option")).map((o) => [o.value, o.textContent]);
    expect(options).toEqual([["ALL", "All Areas"], ["HOC", "HOC"], ["HSC", "HSC"], ["S_PAKNING", "S. Pakning"]]);

    fireEvent.change(select, { target: { value: "HSC" } });
    expect(onAreaChange).toHaveBeenCalledWith("HSC");
    // The area is never sent through the analytics filter callback.
    expect(onFilterChange).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Filter by Pump"), { target: { value: "110-P-1" } });
    const sent = onFilterChange.mock.calls.at(-1)[0];
    expect(sent.pump_tag).toBe("110-P-1");
    expect(sent).not.toHaveProperty("area");
    expect(sent).not.toHaveProperty("contract_area");

    fireEvent.click(screen.getByRole("button", { name: /reset filters/i }));
    expect(onAreaChange).toHaveBeenLastCalledWith("ALL");
  });

  it("lists alias-coded pumps under their canonical area", () => {
    render(<LtsaGlobalFilterBar area="S_PAKNING" authorizedAreas={authorizedAreas} filterOptions={filterOptions} />);
    const pumps = Array.from(screen.getByLabelText("Filter by Pump").querySelectorAll("option")).map((o) => o.value);
    expect(pumps).toEqual(["", "SPK-P-1"]);
    expect(screen.getByTestId("selected-area-badge").textContent).toBe("S. Pakning");
  });
});

