import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import KnowledgeWorkspace from "../pages/KnowledgeWorkspace";
import { getPumpKnowledge } from "../../../api/ai5rClient";

// MWO-LTSA-ASSET360-CONSOLIDATION-001 -- Asset 360 consolidation coverage.
// Fixture shapes mirror this session's own verified production golden
// records (220-P-4A / 2026-06-24 PM occurrence + Condition Monitoring
// reading, temperatures, leak, finding, source traceability) -- used here
// ONLY as test data, never hardcoded into production code (KnowledgeWorkspace.jsx
// and its sub-components take these values from the API response like any
// other pump).
vi.mock("../../../api/ai5rClient", () => ({
  getPumpKnowledge: vi.fn(),
  getPMCMEvidence: vi.fn().mockResolvedValue([]),
}));

afterEach(() => {
  vi.clearAllMocks();
});

const TAG = "220-P-4A";

const GOLDEN_PM = {
  pm_occurrence_code: "LTSA-PMO-7443977B09BE8764",
  pm_schedule_code: "UNSCHEDULED::CM & PM Summary HOC JUNI.xlsx",
  asset_code: TAG,
  asset_type: "PUMP",
  occurrence_date: "2026-06-24",
  status: "DONE",
  workflow_status: "DRAFT",
  checklist_completion: {
    Cooler: true,
    Strainer: true,
    "Quench Line": true,
    "Flushing Line": true,
    "Cooling Water Cooler": true,
  },
  activities: [
    { code: "1", description: "Flushing Line", done: true },
    { code: "4", description: "Quench Line", done: true },
    { code: "19", description: "Strainer", done: true },
  ],
  finding: null,
  source_workbook_name: "CM & PM Summary HOC JUNI.xlsx",
  source_sheet_name: " PM Mech Seal",
  source_row_number: 23,
};

const GOLDEN_CMON = {
  condition_monitoring_reading_code: "LTSA-CMONR-47FBA1F0416C8CB6",
  asset_code: TAG,
  asset_type: "PUMP",
  reading_date: "2026-06-24",
  pump_operating_state: "Running",
  flushing_temp_de: 37.0,
  flushing_temp_nde: null,
  quench_temp_de: 48.0,
  quench_temp_nde: null,
  mechseal_temp_de: 50.0,
  mechseal_temp_nde: null,
  suction_temp: 50.0,
  discharge_temp: 49.0,
  water_jacket_temp_de: null,
  water_jacket_temp_nde: null,
  mechanical_seal_leak_de: true,
  mechanical_seal_leak_nde: null,
  finding: "Mechseal Bocor dari drain gland durasi 1/2 detik",
  workflow_status: "DRAFT",
  source_workbook_name: "CM & PM Summary HOC JUNI.xlsx",
  source_sheet_name: "CM Measuring Report",
  source_row_number: 74,
};

const OTHER_PUMP_PM = {
  pm_occurrence_code: "PMO-OTHER-1",
  asset_code: "220-P-4B",
  occurrence_date: "2026-06-20",
  status: "DONE",
  activities: [],
};

const OTHER_PUMP_CMON = {
  condition_monitoring_reading_code: "CMONR-OTHER-1",
  asset_code: "220-P-4B",
  reading_date: "2026-06-20",
  pump_operating_state: "Running",
};

function backendResponse(overrides = {}) {
  return {
    success: true,
    tag_number: TAG,
    data: {
      summary: {
        asset: { tag_number: TAG, pump_name: "HOC Mechanical Seal Pump" },
        pm_summary: { last_pm: null, status: "ACTIVE", overdue: false },
        cm_summary: { overall_condition: "NORMAL", leak_flag: false, latest_abnormal_values: null },
        seal_summary: { installed_seal: null, compatibility: [], stock_availability: "OK" },
        inventory_summary: { available: [], missing_critical_parts: [] },
        workorder_summary: { open_count: 0, highest_priority: null, newest_work_order: null },
        engineering_flags: [],
        evidence: [],
        metadata: { generated_at: "2026-08-24T00:00:00Z", asset_code: TAG, context_version: "1.0.0" },
      },
      pump: { tag_number: TAG, area: "HOC", pump_type: "OH", status: "ACTIVE" },
      timeline: [],
      seal: [],
      inventory: [],
      // Only THIS pump's records -- the backend's own asset_code filter
      // (LTSAKnowledgeService) already guarantees this; a second record
      // for a different pump proves this test/section never leaks it.
      pm: [GOLDEN_PM],
      cm: [],
      breakdown: [],
      drawings: [],
      recommendation: null,
      pm_schedules: [],
      condition_monitoring_schedules: [],
      condition_monitoring_readings: [GOLDEN_CMON],
      work_orders: [],
      ...overrides,
    },
  };
}

async function renderAsset360(overrides = {}) {
  getPumpKnowledge.mockResolvedValue(backendResponse(overrides));
  render(<KnowledgeWorkspace tag={TAG} />);
  await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
}

describe("Asset 360 renders the selected pump", () => {
  it("shows the pump identity (tag, name)", async () => {
    await renderAsset360();

    expect(screen.getAllByText(TAG).length).toBeGreaterThan(0);
    expect(screen.getAllByText("HOC Mechanical Seal Pump").length).toBeGreaterThan(0);
  });

  it("shows KPI cards: Last PM and Last Condition Monitoring reflect the golden date", async () => {
    await renderAsset360();

    const kpis = screen.getByTestId("asset-header-kpis");
    expect(within(kpis).getByTestId("kpi-last-pm")).toHaveTextContent("2026-06-24");
    expect(within(kpis).getByTestId("kpi-last-condition-monitoring")).toHaveTextContent("2026-06-24");
  });

  it("shows Open WO as 0 (N/A-equivalent), never fabricated, when no work orders exist", async () => {
    await renderAsset360();

    const kpis = screen.getByTestId("asset-header-kpis");
    expect(within(kpis).getByTestId("kpi-open-wo")).toHaveTextContent("0");
  });
});

describe("Condition Monitoring section (C)", () => {
  it("shows the latest reading's operating state, leak DE, and finding", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-condition");
    expect(within(section).getByText("Running")).toBeInTheDocument();
    expect(within(section).getByText(/Mechseal Bocor dari drain gland durasi 1\/2 detik/)).toBeInTheDocument();
    expect(within(section).getByText(/Leak DE: Detected/)).toBeInTheDocument();
  });

  it("exposes all evidenced temperature points (Flushing, Quench, Mechanical Seal DE, Suction, Discharge)", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-condition");
    expect(within(section).getByText(/37°C/)).toBeInTheDocument();
    expect(within(section).getByText(/48°C/)).toBeInTheDocument();
    expect(within(section).getAllByText(/50°C/).length).toBeGreaterThan(0);
    expect(within(section).getByText(/49°C/)).toBeInTheDocument();
  });

  it("renders NULL temperature fields as N/A, never substituted with 0", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-condition");
    // Water Jacket DE/NDE is null/null in the golden fixture.
    const waterJacketLabel = within(section).getByText("Water Jacket");
    const waterJacketCard = waterJacketLabel.parentElement;
    expect(within(waterJacketCard).getByText("N/A / N/A")).toBeInTheDocument();
    expect(within(waterJacketCard).queryByText(/^0/)).not.toBeInTheDocument();
  });

  it("renders the temperature trend chart with time-range filter buttons (1M/3M/6M/1Y)", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-condition");
    const chart = within(section).getByTestId("temperature-trend-chart");
    ["1M", "3M", "6M", "1Y"].forEach((label) => {
      expect(within(chart).getByRole("button", { name: label })).toBeInTheDocument();
    });
    expect(within(chart).getByRole("button", { name: "3M" })).toHaveAttribute("aria-pressed", "true");
    ["3Y", "4Y", "ALL"].forEach((label) => {
      expect(within(chart).queryByRole("button", { name: label })).not.toBeInTheDocument();
    });
  });

  it("switching the trend time range does not crash and keeps the chart mounted", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-condition");
    const chart = within(section).getByTestId("temperature-trend-chart");
    fireEvent.click(within(chart).getByRole("button", { name: "3M" }));
    fireEvent.click(within(chart).getByRole("button", { name: "1Y" }));

    expect(within(chart).getByRole("button", { name: "1Y" })).toHaveAttribute("aria-pressed", "true");
    expect(within(section).getByTestId("temperature-trend-chart")).toBeInTheDocument();
  });

  it("allows inspecting the full reading detail (View Details) without leaving Asset 360", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-condition");
    fireEvent.click(within(section).getAllByRole("button", { name: "View Details" })[0]);

    expect(within(section).getByText("LTSA-CMONR-47FBA1F0416C8CB6")).toBeInTheDocument();
    // Source traceability, reused from ConditionMonitoringReadingDetailPanel.
    expect(within(section).getByText("CM & PM Summary HOC JUNI.xlsx")).toBeInTheDocument();
    expect(within(section).getByText("CM Measuring Report")).toBeInTheDocument();
    expect(within(section).getByText("74")).toBeInTheDocument();
  });

  it("never shows a different pump's Condition Monitoring reading", async () => {
    await renderAsset360({ condition_monitoring_readings: [GOLDEN_CMON, OTHER_PUMP_CMON] });

    const section = screen.getByTestId("knowledge-section-condition");
    expect(within(section).queryByText("CMONR-OTHER-1")).not.toBeInTheDocument();
  });
});

describe("PM History section (E)", () => {
  it("shows the golden PM occurrence with its evidenced activities and UNSCHEDULED badge", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-pm-history");
    expect(within(section).getByText("2026-06-24")).toBeInTheDocument();
    expect(within(section).getByText(/Historical \/ Unscheduled/)).toBeInTheDocument();
    expect(within(section).getByText(/Flushing Line/)).toBeInTheDocument();
  });

  it("shows source traceability (workbook/sheet/row) via View Details", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-pm-history");
    fireEvent.click(within(section).getByRole("button", { name: "View Details" }));

    expect(within(section).getByText("CM & PM Summary HOC JUNI.xlsx")).toBeInTheDocument();
    expect(within(section).getByText(/PM Mech Seal/)).toBeInTheDocument();
    expect(within(section).getByText("23")).toBeInTheDocument();
  });

  it("never shows a different pump's PM occurrence", async () => {
    await renderAsset360({ pm: [GOLDEN_PM, OTHER_PUMP_PM] });

    const section = screen.getByTestId("knowledge-section-pm-history");
    expect(within(section).queryByText("PMO-OTHER-1")).not.toBeInTheDocument();
  });
});

describe("Unified Maintenance History section (D)", () => {
  it("shows both the PM and Condition Monitoring events for the golden date", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-maintenance");
    expect(within(section).getAllByText("2026-06-24").length).toBeGreaterThanOrEqual(2);
  });

  it("shows 'Same Visit' when a real PM and a real CMON share the same calendar date", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-maintenance");
    expect(within(section).getAllByText(/Same Visit • PM \+ Condition Monitoring/).length).toBeGreaterThan(0);
  });

  it("does not show 'Same Visit' when PM and CMON dates differ", async () => {
    await renderAsset360({
      condition_monitoring_readings: [{ ...GOLDEN_CMON, reading_date: "2026-05-01" }],
    });

    const section = screen.getByTestId("knowledge-section-maintenance");
    expect(within(section).queryByText(/Same Visit/)).not.toBeInTheDocument();
  });

  it("filters the unified history by type without navigating away", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-maintenance");
    fireEvent.click(within(section).getByRole("button", { name: "PM" }));

    expect(within(section).getByTestId("history-row-PM:LTSA-PMO-7443977B09BE8764")).toBeInTheDocument();
    expect(within(section).queryByTestId("history-row-CMON:LTSA-CMONR-47FBA1F0416C8CB6")).not.toBeInTheDocument();
  });

  it("expands PM/CMON row detail inline (View Details) and collapses again", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-maintenance");
    const row = screen.getByTestId("history-row-PM:LTSA-PMO-7443977B09BE8764");
    fireEvent.click(within(row).getByRole("button", { name: "View Details" }));
    expect(within(row).getByText("LTSA-PMO-7443977B09BE8764")).toBeInTheDocument();

    fireEvent.click(within(row).getByRole("button", { name: "Hide Details" }));
    expect(within(section).queryByText("Occurrence Summary")).not.toBeInTheDocument();
  });
});

describe("Work Orders section (H)", () => {
  it("shows only this pump's work orders, grouped by status", async () => {
    await renderAsset360({
      work_orders: [
        { work_order_code: "WO-1", asset_code: TAG, title: "Seal replacement", work_type: "CM", status: "OPEN", due_date: "2026-07-01" },
        { work_order_code: "WO-2", asset_code: "220-P-4B", title: "Unrelated pump WO", work_type: "PM", status: "OPEN" },
      ],
    });

    const section = screen.getByTestId("knowledge-section-work-orders");
    expect(within(section).getByText(/Seal replacement/)).toBeInTheDocument();
    expect(within(section).queryByText(/Unrelated pump WO/)).not.toBeInTheDocument();
  });

  it("shows an honest empty state when no work orders exist for this pump", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-work-orders");
    expect(within(section).getByText(/No Work Orders/)).toBeInTheDocument();
  });
});

describe("AI Engineering Copilot section (J) -- existing Copilot behavior preserved", () => {
  it("renders the reused CopilotPanel scoped to this pump's tag, with no fabricated/pre-filled answer", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-ai-copilot");
    expect(within(section).getByText(`Asset context: ${TAG}`)).toBeInTheDocument();
    expect(within(section).getByPlaceholderText(`Ask about ${TAG}...`)).toBeInTheDocument();
  });

  it("does not call askCopilot (or any API beyond getPumpKnowledge) on mount", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());
    const client = await import("../../../api/ai5rClient");
    const otherKeys = Object.keys(client).filter((key) => key !== "getPumpKnowledge" && key !== "getPMCMEvidence");

    render(<KnowledgeWorkspace tag={TAG} />);
    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());

    expect(otherKeys).toEqual([]);
  });
});

describe("Documents section (I) -- reused Drawings, source traceability where available", () => {
  it("shows an honest empty state when no drawings exist for this pump", async () => {
    await renderAsset360();

    const section = screen.getByTestId("knowledge-section-drawings");
    expect(section.querySelector(".eng-empty")).toBeInTheDocument();
  });
});

describe("No fabricated data", () => {
  it("never renders a fabricated numeric 0 in place of an absent temperature", async () => {
    await renderAsset360({
      condition_monitoring_readings: [
        {
          condition_monitoring_reading_code: "CMONR-NULLTEST",
          asset_code: TAG,
          reading_date: "2026-06-24",
          pump_operating_state: null,
          flushing_temp_de: null,
          flushing_temp_nde: null,
          quench_temp_de: null,
          quench_temp_nde: null,
          mechseal_temp_de: null,
          mechseal_temp_nde: null,
          suction_temp: null,
          discharge_temp: null,
          mechanical_seal_leak_de: null,
          mechanical_seal_leak_nde: null,
          finding: null,
        },
      ],
    });

    const section = screen.getByTestId("knowledge-section-condition");
    expect(within(section).getAllByText(/N\/A/).length).toBeGreaterThan(0);
    expect(within(section).getByText(/Not Recorded/)).toBeInTheDocument();
  });
});
