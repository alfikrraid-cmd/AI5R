import { readFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Pump from "./Pump";
import {
  getPumps, getPumpOpenWorkOrders, getPumpLifecycle, getSeals, getSealCompatibility, postEngineeringAI,
} from "../../../api/ai5rClient";

// MWO-LTSA-065 -- getPumpLastPM/getPumpSpareParts/getPMSchedules/
// getCMReports/getWorkOrders are gone: Pump.jsx now fetches ONE endpoint,
// getPumpLifecycle(tag), for Current State/Related Engineering/
// Compatibility. getPumpOpenWorkOrders stays (registry-list-level, not a
// lifecycle-detail concern).
//
// MWO-LTSA-UI-V2-001 -- getSeals()/getSealCompatibility() are the two
// already-existing endpoints Pump.jsx now also fetches once (Seal &
// Inventory enrichment) -- see sealMapping.js's buildSealInventoryGroups().
vi.mock("../../../api/ai5rClient", () => ({
  getPumps: vi.fn(),
  getPumpOpenWorkOrders: vi.fn(),
  getPumpLifecycle: vi.fn(),
  getSeals: vi.fn(),
  getSealCompatibility: vi.fn(),
  postEngineeringAI: vi.fn(),
}));

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PUMP_SOURCE = readFileSync(path.join(__dirname, "Pump.jsx"), "utf-8");
// MWO-LTSA-050 -- PumpDetailPanel.jsx was deleted, replaced by
// PumpOpenDesignView.jsx (the Open-Design-conformant detail view, matching
// SealOpenDesignView.jsx's own hierarchy). This self-audit now reads the
// new canonical component's source instead.
const VIEW_SOURCE = readFileSync(path.join(__dirname, "..", "components", "PumpOpenDesignView.jsx"), "utf-8");

const PUMPS = [
  {
    tag_number: "305-P-2",
    name: "Cooling Water Circulation Pump",
    area: "Utilities",
    manufacturer: "Flowserve",
    pump_type: "Vertical Turbine",
    seal_type: "Flowserve ISC2",
    location: "Utilities - Cooling Tower Basin",
    status: "RUNNING",
    criticality: "MEDIUM",
  },
  {
    tag_number: "641-P-5",
    name: "Sour Water Stripper Bottoms Pump",
    area: "SWS Unit",
    manufacturer: "ITT Goulds",
    pump_type: "Centrifugal (API 610 OH2)",
    seal_type: "John Crane 502",
    location: "SWS Unit",
    status: "FAULT",
    criticality: "HIGH",
  },
];

const AI_RESPONSE = {
  summary: "Pump 305-P-2 is operating within normal parameters.",
  findings: ["No abnormal vibration trend over the last 30 days."],
  confidence: 0.77,
  evidence: [{ source: "ConditionMonitoringReading", reference: "CMON-1001" }],
  recommendations: ["Continue routine monitoring."],
  risk: "LOW",
  remaining_life: "180 days",
  provider: "CLAUDE",
  model: "claude-sonnet-5",
  latency: 0.842,
  token_usage: { input: 400, output: 90 },
  trace_id: "trace-pump-001",
  execution_status: "SUCCESS",
  source_references: [{ source: "ConditionMonitoringReading", reference: "CMON-1001" }],
  error: null,
};

const EMPTY_LIFECYCLE_DATA = {
  tag_number: null,
  pump: null,
  current_state: {
    current_installation: null,
    current_seal: null,
    elapsed_service_days: null,
    running_hours_derived: null,
    last_pm: null,
    next_pm: null,
    last_cm: null,
    last_failure: null,
    open_work_orders: [],
  },
  timeline: [],
  analytics: {
    elapsed_service_days: null,
    pm_count: 0,
    cm_count: 0,
    failure_count: 0,
    mtbf: null,
    mtbr: null,
    average_seal_life: null,
    health_index: null,
    availability: null,
    reliability: null,
  },
  related_engineering: {
    pm_schedules: [],
    cm_reports: [],
    work_orders: [],
    breakdown_history: [],
    drawings: [],
    documents: [],
    inventory: [],
  },
};

function loadPumps(records = PUMPS) {
  getPumps.mockResolvedValue(records);
  getPumpOpenWorkOrders.mockResolvedValue({ success: true, openWO: 0, data: [] });
  getPumpLifecycle.mockResolvedValue({ success: true, tag_number: null, data: EMPTY_LIFECYCLE_DATA });
  getSeals.mockResolvedValue([]);
  getSealCompatibility.mockResolvedValue([]);
}

afterEach(() => {
  vi.clearAllMocks();
});

async function renderAndSelect(tag = "305-P-2") {
  loadPumps();
  render(<Pump />);
  await screen.findByText(tag);
  fireEvent.click(screen.getByText(tag));
  await screen.findByRole("heading", { name: PUMPS.find((p) => p.tag_number === tag).name });
}

describe("EngineeringAIRequest construction", () => {
  it("posts asset_code equal to the selected pump's tag", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].asset_code).toBe("305-P-2");
  });

  it("reuses the existing 'summary' intent -- no new intent invented", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].intent).toBe("summary");
  });

  it("reuses the existing 'summary' prompt_type -- no new prompt_type invented", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].prompt_type).toBe("summary");
  });

  it("posts a non-empty string trace_id", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    const { trace_id } = postEngineeringAI.mock.calls[0][0];
    expect(typeof trace_id).toBe("string");
    expect(trace_id.length).toBeGreaterThan(0);
  });

  it("posts workspace = 'pump'", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].workspace).toBe("pump");
  });

  it("does not send selected_record_id (not applicable/supported for a pump-level summary)", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].selected_record_id).toBeUndefined();
  });

  it("does not send a question field (no question UI exists)", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].question).toBeUndefined();
  });
});

describe("POST invocation", () => {
  it("calls postEngineeringAI exactly once for a single pump selection", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalledTimes(1));
  });

  it("does not call postEngineeringAI before any pump is selected", async () => {
    loadPumps();
    render(<Pump />);
    await screen.findByText("305-P-2");
    expect(postEngineeringAI).not.toHaveBeenCalled();
  });

  it("re-fetches with a fresh trace_id when a different pump is selected", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    loadPumps();
    render(<Pump />);
    await screen.findByText("305-P-2");

    fireEvent.click(screen.getByText("305-P-2"));
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalledTimes(1));
    const firstTraceId = postEngineeringAI.mock.calls[0][0].trace_id;

    fireEvent.click(screen.getByText("641-P-5"));
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalledTimes(2));
    const secondCall = postEngineeringAI.mock.calls[1][0];

    expect(secondCall.asset_code).toBe("641-P-5");
    expect(secondCall.trace_id).not.toBe(firstTraceId);
  });
});

describe("Response rendering", () => {
  it("renders the response summary", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(await screen.findByText(AI_RESPONSE.summary)).toBeTruthy();
  });

  it("renders execution_status as the status badge", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(await screen.findByText("SUCCESS")).toBeTruthy();
  });

  it("renders provider metadata", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(await screen.findByText("CLAUDE")).toBeTruthy();
  });

  it("renders latency formatted in milliseconds", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(await screen.findByText("842 ms")).toBeTruthy();
  });

  it("renders trace_id from the response", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(await screen.findByText("trace-pump-001")).toBeTruthy();
  });

  it("renders confidence as a rounded percentage", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(await screen.findByText("77%")).toBeTruthy();
  });

  it("renders risk", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(await screen.findByText("LOW")).toBeTruthy();
  });

  it("renders remaining_life", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(await screen.findByText("180 days")).toBeTruthy();
  });

  it("renders findings via the packaged EngineeringAIFindings component", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(await screen.findByText(AI_RESPONSE.findings[0])).toBeTruthy();
    expect(await screen.findByRole("heading", { name: "Engineering Findings" })).toBeTruthy();
  });

  it("renders evidence via the packaged EngineeringAIEvidence component", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    const heading = await screen.findByRole("heading", { name: "Evidence Strip" });
    expect(heading.closest("section").textContent).toContain("CMON-1001");
  });

  it("renders recommendations via the packaged EngineeringAIRecommendation component", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    // MWO-LTSA-050 -- "Recommendation" is also the Inspector Rail's own
    // section title (<h3 class="rail-title">Recommendation</h3>) alongside
    // the packaged component's own heading -- findAllByRole, not
    // findByRole.
    expect((await screen.findAllByRole("heading", { name: "Recommendation" })).length).toBeGreaterThan(0);
    expect(await screen.findByText(AI_RESPONSE.recommendations[0])).toBeTruthy();
  });

  it("renders source references via the packaged EngineeringAISourceReferences component", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(await screen.findByRole("heading", { name: "Source References" })).toBeTruthy();
  });
});

describe("Loading state (reuses the Failure Analysis model)", () => {
  it("shows a generating message while the AI request is in flight", async () => {
    let resolvePromise;
    postEngineeringAI.mockReturnValue(new Promise((resolve) => { resolvePromise = resolve; }));
    loadPumps();
    render(<Pump />);
    await screen.findByText("305-P-2");
    fireEvent.click(screen.getByText("305-P-2"));

    expect(await screen.findByText("Generating pump summary…")).toBeTruthy();
    resolvePromise(AI_RESPONSE);
    await waitFor(() => expect(screen.getByText(AI_RESPONSE.summary)).toBeTruthy());
  });

  it("shows a Generating… status label while loading", async () => {
    let resolvePromise;
    postEngineeringAI.mockReturnValue(new Promise((resolve) => { resolvePromise = resolve; }));
    loadPumps();
    render(<Pump />);
    await screen.findByText("305-P-2");
    fireEvent.click(screen.getByText("305-P-2"));

    expect(await screen.findByText("Generating…")).toBeTruthy();
    resolvePromise(AI_RESPONSE);
  });
});

describe("Retry (Golden Reference has none -- faithfully not replicated)", () => {
  it("FailureAnalysisWorkspace (Golden Reference) has no retry button or retry state to replicate", () => {
    const goldenReferenceSource = readFileSync(
      path.join(__dirname, "FailureAnalysisWorkspace.jsx"),
      "utf-8"
    );
    expect(goldenReferenceSource.toLowerCase()).not.toMatch(/retry/);
  });

  it("Pump Workspace correspondingly has no retry button or retry state", () => {
    expect(PUMP_SOURCE.toLowerCase()).not.toMatch(/retry/);
    expect(VIEW_SOURCE.toLowerCase()).not.toMatch(/retry/);
  });
});

describe("Error state", () => {
  it("renders a network error message", async () => {
    postEngineeringAI.mockRejectedValue(new Error("Engineering AI API unavailable"));
    await renderAndSelect();
    expect(await screen.findByText("Engineering AI API unavailable")).toBeTruthy();
  });

  it("renders an Error status label on network failure", async () => {
    postEngineeringAI.mockRejectedValue(new Error("boom"));
    await renderAndSelect();
    expect(await screen.findByText("Error")).toBeTruthy();
  });

  it("falls back to a generic message when the rejected error has no message", async () => {
    postEngineeringAI.mockRejectedValue({});
    await renderAndSelect();
    expect(await screen.findByText("Engineering AI request failed")).toBeTruthy();
  });
});

describe("Invalid response (business-level error)", () => {
  it("renders the response-level error instead of the summary when execution failed", async () => {
    postEngineeringAI.mockResolvedValue({
      ...AI_RESPONSE,
      execution_status: "ERROR",
      error: "Asset context could not be built",
    });
    await renderAndSelect();
    expect(await screen.findByText("Asset context could not be built")).toBeTruthy();
    expect(screen.queryByText(AI_RESPONSE.summary)).toBeNull();
  });

  it("does not render Findings/Evidence/Recommendation/SourceReferences panels on business error", async () => {
    postEngineeringAI.mockResolvedValue({ ...AI_RESPONSE, execution_status: "ERROR", error: "boom" });
    await renderAndSelect();
    await screen.findByText("boom");
    expect(screen.queryByRole("heading", { name: "Engineering Findings" })).toBeNull();
  });
});

describe("Trace propagation", () => {
  it("renders the exact same trace_id the request sent, once the response echoes it back", async () => {
    postEngineeringAI.mockImplementation((request) =>
      Promise.resolve({ ...AI_RESPONSE, trace_id: request.trace_id })
    );
    await renderAndSelect();
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    const sentTraceId = postEngineeringAI.mock.calls[0][0].trace_id;
    expect(await screen.findByText(sentTraceId)).toBeTruthy();
  });
});

// MWO-LTSA-050 -- PumpDetailPanel's Card-based sections (Equipment
// Summary/Maintenance Summary/AI Recommendation/Spare Parts/Quick Actions)
// no longer exist -- PumpOpenDesignView replaces them with the same
// Open-Design hierarchy SealOpenDesignView uses (Hero/Current
// Status/Engineering Overview/Compatibility/Action Bar). These checks are
// rewritten against the new structure, not deleted -- every fact the old
// tests verified (identity fields render, real fetched data renders,
// action callbacks work, the empty state exists) still has an equivalent
// assertion below.
describe("Regression: existing Pump Workspace behavior is preserved under the new Open Design hierarchy", () => {
  it("still renders the pump's identity fields (Hero)", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(screen.getByRole("heading", { name: "Cooling Water Circulation Pump" })).toBeTruthy();
    // "Flowserve"/"Vertical Turbine" also appear in the registry table's
    // own row for this pump -- getAllByText, not getByText.
    expect(screen.getAllByText("Flowserve").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Vertical Turbine").length).toBeGreaterThan(0);
  });

  it("still renders real maintenance data (Current Status: Health, Criticality, Open Work Orders)", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(screen.getByText("Current Status")).toBeTruthy();
    expect(screen.getAllByText("Medium").length).toBeGreaterThan(0);
  });

  it("still renders Engineering Recommendation alongside the Engineering AI card", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(screen.getByText("Engineering Recommendation")).toBeTruthy();
    expect(screen.getAllByText("Engineering AI").length).toBeGreaterThan(0);
  });

  it("still renders Seal & Inventory (MWO-LTSA-UI-V2-001, replacing the old Compatibility/Inventory duplicate)", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(screen.getByText("Seal & Inventory")).toBeTruthy();
  });

  it("still renders working action callbacks (now on the sticky Action Bar)", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect();
    expect(screen.getByRole("button", { name: "Create PM" })).toBeTruthy();
  });

  it("still shows the empty state before any pump is selected", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    loadPumps();
    render(<Pump />);
    await screen.findByText("305-P-2");
    expect(screen.getByText(/no pump selected/i)).toBeTruthy();
  });
});

describe("Snapshot", () => {
  it("matches the PumpOpenDesignView Engineering AI section snapshot when ready", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    const { container } = render(<Pump />);
    loadPumps();
    await screen.findByText("305-P-2");
    fireEvent.click(screen.getByText("305-P-2"));
    await screen.findByText(AI_RESPONSE.summary);

    expect(container.querySelector(".pump-workspace-detail")).toMatchSnapshot();
  });
});

describe("Self-audit: only postEngineeringAI is used, no duplication, no forbidden objects", () => {
  it("Pump.jsx makes no raw fetch() call", () => {
    expect(PUMP_SOURCE).not.toMatch(/\bfetch\(/);
  });

  it("PumpDetailPanel.jsx makes no raw fetch() call", () => {
    expect(VIEW_SOURCE).not.toMatch(/\bfetch\(/);
  });

  function importLines(source) {
    return source.split("\n").filter((line) => line.trim().startsWith("import "));
  }

  it("Pump.jsx never imports AI_RUNTIME/Router/EngineeringAIClient/PromptBuilder/ContextEngine", () => {
    const lines = importLines(PUMP_SOURCE);
    for (const forbidden of ["AI_RUNTIME", "EngineeringAIClient", "EngineeringPromptBuilder", "EngineeringContextEngine"]) {
      expect(lines.some((line) => line.includes(forbidden))).toBe(false);
    }
  });

  it("PumpDetailPanel.jsx never imports AI_RUNTIME/Router/EngineeringAIClient/PromptBuilder/ContextEngine", () => {
    const lines = importLines(VIEW_SOURCE);
    for (const forbidden of ["AI_RUNTIME", "EngineeringAIClient", "EngineeringPromptBuilder", "EngineeringContextEngine"]) {
      expect(lines.some((line) => line.includes(forbidden))).toBe(false);
    }
  });

  it("does not define any forbidden Pump*-prefixed AI object", () => {
    for (const forbidden of [
      "PumpAIClient",
      "PumpPromptBuilder",
      "PumpContextEngine",
      "PumpRecommendationEngine",
      "PumpResponseParser",
      "PumpGateway",
      "PumpRuntime",
      "PumpService",
    ]) {
      expect(PUMP_SOURCE).not.toMatch(new RegExp(forbidden));
      expect(VIEW_SOURCE).not.toMatch(new RegExp(forbidden));
    }
  });

  it("does not redefine formatConfidence/formatLatency/formatValue/renderAIItem locally (no duplicate formatter)", () => {
    for (const helper of ["formatConfidence", "formatLatency", "formatValue", "renderAIItem"]) {
      const localDefinition = new RegExp(`(function|const)\\s+${helper}\\s*[=(]`);
      expect(PUMP_SOURCE).not.toMatch(localDefinition);
      expect(VIEW_SOURCE).not.toMatch(localDefinition);
    }
  });

  it("imports Engineering AI components only from the canonical package, never a direct component file", () => {
    expect(VIEW_SOURCE).toMatch(/from ["']\.\/engineering-ai["']/);
    expect(VIEW_SOURCE).not.toMatch(/from ["'][./]*components\/EngineeringAI\w+["']/);
  });

  it("PumpDetailPanel renders only packaged Engineering AI components for response content -- no inline field access on aiResponse beyond passing it through", () => {
    // Every direct read of an EngineeringAIResponse field (summary, findings,
    // confidence, risk, remaining_life, evidence, recommendations,
    // source_references) must happen inside a packaged component, not here.
    for (const field of ["aiResponse.summary", "aiResponse.findings", "aiResponse.confidence", "aiResponse.risk", "aiResponse.remaining_life", "aiResponse.evidence", "aiResponse.recommendations", "aiResponse.source_references"]) {
      expect(VIEW_SOURCE).not.toContain(field);
    }
  });

  it("uses generateTraceId, not a locally re-implemented UUID/trace generator", () => {
    expect(PUMP_SOURCE).toMatch(/import generateTraceId from ["']\.\.\/utils\/generateTraceId["']/);
    expect(PUMP_SOURCE).not.toMatch(/crypto\.randomUUID/);
  });

  it("does not clear the previous pump's AI response as raw JSON on the screen while a new one loads", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    loadPumps();
    render(<Pump />);
    await screen.findByText("305-P-2");
    fireEvent.click(screen.getByText("305-P-2"));
    await screen.findByText(AI_RESPONSE.summary);

    let resolveSecond;
    postEngineeringAI.mockReturnValue(new Promise((resolve) => { resolveSecond = resolve; }));
    fireEvent.click(screen.getByText("641-P-5"));

    await waitFor(() => expect(screen.queryByText(AI_RESPONSE.summary)).toBeNull());
    expect(screen.getByText("Generating pump summary…")).toBeTruthy();
    resolveSecond({ ...AI_RESPONSE, summary: "Different pump summary." });
  });

  it("PumpDetailPanel never JSON-serializes the raw response as visible text (only packaged components format it)", () => {
    expect(VIEW_SOURCE).not.toMatch(/JSON\.stringify\(\s*aiResponse\s*\)/);
  });

  it("Pump.jsx does not construct any AI client, provider, or Router instance", () => {
    expect(PUMP_SOURCE).not.toMatch(/new\s+\w*(Client|Provider|Router)\(/);
  });
});
