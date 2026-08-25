import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ConditionMonitoringWorkspace from "./ConditionMonitoringWorkspace";
import {
  getConditionMonitoringReadings,
  getConditionMonitoringReadingsPage,
  getConditionMonitoringSchedules,
  getPumps,
  postEngineeringAI,
  getPMSchedules,
  getCMReports,
} from "../../../api/ai5rClient";

// MWO-LTSA-061 -- Condition Monitoring Operationalization. This file
// covers the non-AI regression surface (Engineering AI request/response
// behavior is already fully covered by
// ConditionMonitoringWorkspace.engineeringAI.test.jsx and is untouched by
// this MWO): real readings rendering, historical readings, honest
// threshold/alert interpretation, and the real Related PM/Related Failure
// Analysis relationships this MWO added. No dedicated
// ConditionMonitoringWorkspace.test.jsx existed before this MWO.
vi.mock("../../../api/ai5rClient", () => ({
  getConditionMonitoringReadings: vi.fn(),
  getConditionMonitoringReadingsPage: vi.fn(),
  getConditionMonitoringSchedules: vi.fn(),
  getPumps: vi.fn(),
  postEngineeringAI: vi.fn(),
  getPMSchedules: vi.fn(),
  getCMReports: vi.fn(),
}));

const PUMPS = [
  {
    tag_number: "641-P-5",
    name: "Sour Water Stripper Bottoms Pump",
    area: "SWS Unit",
    manufacturer: "ITT Goulds",
    pump_type: "Centrifugal (API 610 OH2)",
    seal_type: "John Crane 502",
    location: "SWS Unit",
    status: "RUNNING",
    criticality: "HIGH",
  },
];

const SCHEDULES = [
  {
    condition_monitoring_schedule_code: "CMON-SCHED-001",
    asset_code: "641-P-5",
    frequency: "WEEKLY",
    applicable_parameters: ["mechseal_temp", "mechanical_seal_leak"],
  },
];

const READINGS = [
  {
    condition_monitoring_reading_code: "CMON-READ-101",
    condition_monitoring_schedule_code: "CMON-SCHED-001",
    asset_code: "641-P-5",
    reading_date: "2026-07-12",
    flushing_temp_de: 68,
    flushing_temp_nde: 65,
    quench_temp_de: 45,
    quench_temp_nde: 44,
    mechseal_temp_de: 84,
    mechseal_temp_nde: 79,
    mechanical_seal_leak_de: true,
    mechanical_seal_leak_nde: false,
    suction_temp: 42,
    discharge_temp: 58,
    pump_operating_state: "RUNNING",
  },
  {
    condition_monitoring_reading_code: "CMON-READ-100",
    condition_monitoring_schedule_code: "CMON-SCHED-001",
    asset_code: "641-P-5",
    reading_date: "2026-07-05",
    flushing_temp_de: 66,
    flushing_temp_nde: 64,
    mechseal_temp_de: 80,
    mechseal_temp_nde: 78,
    mechanical_seal_leak_de: false,
    mechanical_seal_leak_nde: false,
    suction_temp: 41,
    discharge_temp: 57,
  },
];

const PM_SCHEDULES = [
  { pm_schedule_code: "PM-641-P-5-01", asset_code: "641-P-5", procedure: "Quarterly seal inspection", frequency: "QUARTERLY", next_due: "2026-09-01" },
  { pm_schedule_code: "PM-999-P-9-01", asset_code: "999-P-9", procedure: "Unrelated asset PM", frequency: "MONTHLY", next_due: "2026-08-01" },
];

const CM_REPORTS = [
  { cm_report_code: "CM-641-P-5-04", asset_code: "641-P-5", failure_description: "Mechanical seal leak — DE side", status: "OPEN" },
  { cm_report_code: "CM-999-P-9-02", asset_code: "999-P-9", failure_description: "Unrelated asset failure", status: "CLOSED" },
];

function loadCMData({ readings = READINGS, schedules = SCHEDULES, pmSchedules = PM_SCHEDULES, cmReports = CM_REPORTS } = {}) {
  getPumps.mockResolvedValue(PUMPS);
  getConditionMonitoringReadings.mockResolvedValue(readings);
  getConditionMonitoringReadingsPage.mockResolvedValue({ items: readings, total: readings.length, limit: 25, offset: 0 });
  getConditionMonitoringSchedules.mockResolvedValue(schedules);
  getPMSchedules.mockResolvedValue(pmSchedules);
  getCMReports.mockResolvedValue(cmReports);
  postEngineeringAI.mockResolvedValue({
    summary: "", findings: [], confidence: null, evidence: [], recommendations: [],
    risk: null, remaining_life: null, provider: "UNKNOWN", model: "UNKNOWN", latency: 0,
    token_usage: {}, trace_id: "trace-test", execution_status: "SUCCESS", source_references: [], error: null,
  });
}

afterEach(() => {
  vi.clearAllMocks();
});

async function renderAndSelect() {
  loadCMData();
  render(<ConditionMonitoringWorkspace />);
  const select = await screen.findByLabelText("Select Asset");
  fireEvent.change(select, { target: { value: "641-P-5" } });
  await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });
}

describe("Real Condition Monitoring readings render", () => {
  it("renders the bounded primary page while secondary registries remain pending", async () => {
    getConditionMonitoringReadingsPage.mockResolvedValue({ items: READINGS, total: 73, limit: 25, offset: 0 });
    getPumps.mockReturnValue(new Promise(() => {}));
    getConditionMonitoringSchedules.mockReturnValue(new Promise(() => {}));
    getPMSchedules.mockReturnValue(new Promise(() => {}));
    getCMReports.mockReturnValue(new Promise(() => {}));
    postEngineeringAI.mockReturnValue(new Promise(() => {}));

    render(<ConditionMonitoringWorkspace />);

    expect((await screen.findAllByText("2026-07-12")).length).toBeGreaterThan(0);
    expect(screen.queryByText("Loading condition monitoring data...")).toBeNull();
    expect(screen.getByText("1–2 of 73")).toBeTruthy();
    expect(getConditionMonitoringReadingsPage).toHaveBeenCalledWith({ limit: 25, offset: 0 });
  });

  it("keeps readings visible when secondary registries fail", async () => {
    getConditionMonitoringReadingsPage.mockResolvedValue({ items: READINGS, total: 2, limit: 25, offset: 0 });
    getPumps.mockRejectedValue(new Error("secondary unavailable"));
    getConditionMonitoringSchedules.mockRejectedValue(new Error("secondary unavailable"));
    getPMSchedules.mockRejectedValue(new Error("secondary unavailable"));
    getCMReports.mockRejectedValue(new Error("secondary unavailable"));
    postEngineeringAI.mockResolvedValue({ summary: "", findings: [], confidence: null, evidence: [], recommendations: [], risk: null, remaining_life: null, provider: "UNKNOWN", model: "UNKNOWN", latency: 0, token_usage: {}, trace_id: "trace-test", execution_status: "SUCCESS", source_references: [], error: null });

    render(<ConditionMonitoringWorkspace />);

    expect((await screen.findAllByText("2026-07-12")).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "641-P-5" })).toBeTruthy();
  });

  it("requests bounded next and previous pages", async () => {
    getConditionMonitoringReadingsPage.mockImplementation(({ offset }) => Promise.resolve({
      items: offset === 0 ? READINGS : [READINGS[1]], total: 26, limit: 25, offset,
    }));
    postEngineeringAI.mockResolvedValue({ summary: "", findings: [], confidence: null, evidence: [], recommendations: [], risk: null, remaining_life: null, provider: "UNKNOWN", model: "UNKNOWN", latency: 0, token_usage: {}, trace_id: "trace-test", execution_status: "SUCCESS", source_references: [], error: null });
    render(<ConditionMonitoringWorkspace />);

    await screen.findAllByText("2026-07-12");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(getConditionMonitoringReadingsPage).toHaveBeenLastCalledWith({ limit: 25, offset: 25 }));
    expect(screen.getByText("26–26 of 26")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Previous" }));
    await waitFor(() => expect(getConditionMonitoringReadingsPage).toHaveBeenLastCalledWith({ limit: 25, offset: 0 }));
  });

  it("renders the latest reading's flushing/mechseal/suction/discharge values", async () => {
    await renderAndSelect();
    expect(screen.getByText("68 C")).toBeTruthy();
    expect(screen.getByText("84 C")).toBeTruthy();
    expect(screen.getByText("42 C")).toBeTruthy();
    expect(screen.getByText("58 C")).toBeTruthy();
  });

  it("renders quench temperature DE/NDE, a canonical dimension not previously shown", async () => {
    await renderAndSelect();
    expect(screen.getByText("Quench temperature DE")).toBeTruthy();
    expect(screen.getByText("45 C")).toBeTruthy();
    expect(screen.getByText("Quench temperature NDE")).toBeTruthy();
    expect(screen.getByText("44 C")).toBeTruthy();
  });

  it("renders pump operating state as a canonical reading field", async () => {
    await renderAndSelect();
    expect(screen.getByText("Pump operating state")).toBeTruthy();
    expect(screen.getByText("RUNNING")).toBeTruthy();
  });

  it("renders leakage DE/NDE as Observed/Not observed, never a fabricated numeric value", async () => {
    await renderAndSelect();
    expect(screen.getAllByText("Observed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Not observed").length).toBeGreaterThan(0);
  });
});

describe("Historical readings can be inspected", () => {
  it("renders every reading in the pump's history, not just the latest", async () => {
    await renderAndSelect();
    expect(screen.getByText("Measurement history")).toBeTruthy();
    const history = screen.getByTestId("measurement-history");
    expect(history.textContent).toContain("2026-07-12");
    expect(history.textContent).toContain("2026-07-05");
  });

  it("shows an honest empty state when the selected pump has no readings", async () => {
    loadCMData({ readings: [] });
    render(<ConditionMonitoringWorkspace />);
    const select = await screen.findByLabelText("Select Asset");
    fireEvent.change(select, { target: { value: "641-P-5" } });
    await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });
    expect(screen.getByText("Measurement history is not yet available — its backend capability does not exist yet.")).toBeTruthy();
  });
});

describe("Threshold/alert interpretation never fabricates a limit", () => {
  it("discloses that no canonical threshold exists for temperature measurements", async () => {
    await renderAndSelect();
    expect(screen.getByText(/No canonical threshold is defined for temperature measurements/)).toBeTruthy();
    expect(screen.getByText("No canonical threshold defined for temperature measurements.")).toBeTruthy();
  });

  it("lists the mechanical seal leak reading as a real alert (the one real abnormal-condition signal)", async () => {
    await renderAndSelect();
    expect(screen.getByText("Mechanical seal leak observed — DE")).toBeTruthy();
  });

  it("does not list a normal (non-leak) reading as an alert", async () => {
    await renderAndSelect();
    // 2026-07-05 has no leak; its date should not appear inside the alerts section.
    const alertsSection = screen.getByTestId("alerts-section");
    expect(alertsSection.textContent).not.toContain("2026-07-05");
  });

  it("shows an honest empty state when no reading in history has a leak", async () => {
    loadCMData({ readings: [READINGS[1]] });
    render(<ConditionMonitoringWorkspace />);
    const select = await screen.findByLabelText("Select Asset");
    fireEvent.change(select, { target: { value: "641-P-5" } });
    await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });
    expect(screen.getByText("Alerts and alarm history is not yet available — its backend capability does not exist yet.")).toBeTruthy();
  });
});

describe("Pump relationship is canonical", () => {
  it("filters readings, PM, and Failure Analysis by the pump's own tag_number (asset_code), not a fabricated key", async () => {
    await renderAndSelect();
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].asset_code).toBe("641-P-5");
  });
});

describe("Related PM works", () => {
  it("renders the PM schedule matched to this pump's equipment tag", async () => {
    await renderAndSelect();
    expect(screen.getByText("PM-641-P-5-01")).toBeTruthy();
    expect(screen.getByText("Due 2026-09-01")).toBeTruthy();
  });

  it("does not render a PM schedule belonging to a different asset", async () => {
    await renderAndSelect();
    expect(screen.queryByText("PM-999-P-9-01")).toBeNull();
  });

  it("shows an honest empty state when no PM schedule matches", async () => {
    loadCMData({ pmSchedules: [] });
    render(<ConditionMonitoringWorkspace />);
    const select = await screen.findByLabelText("Select Asset");
    fireEvent.change(select, { target: { value: "641-P-5" } });
    await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });
    expect(screen.getByText("No PM schedules matched to this asset.")).toBeTruthy();
  });
});

describe("Related Failure Analysis works", () => {
  it("renders the CM report matched to this pump's equipment tag (FailureAnalysisWorkspace's own real data source)", async () => {
    await renderAndSelect();
    expect(screen.getByText("CM-641-P-5-04")).toBeTruthy();
    expect(screen.getByText("Mechanical seal leak — DE side")).toBeTruthy();
  });

  it("does not render a CM report belonging to a different asset", async () => {
    await renderAndSelect();
    expect(screen.queryByText("CM-999-P-9-02")).toBeNull();
  });

  it("shows an honest empty state when no failure analysis record matches", async () => {
    loadCMData({ cmReports: [] });
    render(<ConditionMonitoringWorkspace />);
    const select = await screen.findByLabelText("Select Asset");
    fireEvent.change(select, { target: { value: "641-P-5" } });
    await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });
    expect(screen.getByText("No failure analysis records matched to this asset.")).toBeTruthy();
  });
});

describe("Engineering recommendation flow reuses the real Engineering AI recommendation", () => {
  it("disables the action bar's Review recommendation button until Engineering AI is ready", async () => {
    loadCMData();
    let resolvePromise;
    postEngineeringAI.mockReturnValue(new Promise((resolve) => { resolvePromise = resolve; }));
    render(<ConditionMonitoringWorkspace />);
    const select = await screen.findByLabelText("Select Asset");
    fireEvent.change(select, { target: { value: "641-P-5" } });
    await screen.findByRole("heading", { name: "Sour Water Stripper Bottoms Pump" });

    expect(screen.getByRole("button", { name: "Review recommendation" }).disabled).toBe(true);
    resolvePromise({
      summary: "ok", findings: [], confidence: null, evidence: [], recommendations: ["Inspect DE seal."],
      risk: null, remaining_life: null, provider: "CLAUDE", model: "m", latency: 0, token_usage: {},
      trace_id: "t", execution_status: "SUCCESS", source_references: [], error: null,
    });
    await waitFor(() => expect(screen.getByRole("button", { name: "Review recommendation" }).disabled).toBe(false));
  });
});

describe("cm (Corrective Maintenance) remains unaffected", () => {
  it("calls getCMReports as a plain, argument-less list read -- never a create/update/delete call", async () => {
    await renderAndSelect();
    expect(getCMReports).toHaveBeenCalledWith();
  });

  it("does not import the CM workspace, its Open Design view, or cmMapping.js -- only reads cm_report via the existing getCMReports()/mapCMReportRecord list path", async () => {
    const { readFileSync } = await import("fs");
    const path = await import("path");
    const { fileURLToPath } = await import("url");
    const dir = path.dirname(fileURLToPath(import.meta.url));
    const source = readFileSync(path.join(dir, "ConditionMonitoringWorkspace.jsx"), "utf-8");
    expect(source).not.toMatch(/from ["'].*\bCMOpenDesignView["']/);
    expect(source).not.toMatch(/from ["']\.\.\/pages\/CM["']/);
    expect(source).toMatch(/from ["']\.\.\/utils\/cmMapping["']/);
  });
});
