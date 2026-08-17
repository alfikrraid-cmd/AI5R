import { readFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Seal from "./Seal";
import { postEngineeringAI, getPMSchedules, getCMReports, getWorkOrders } from "../../../api/ai5rClient";
import sampleSeals from "../data/sampleSeals";

// MWO-LTSA-042A -- Seal.jsx now also fetches Related Engineering (PM/CM/
// Work Orders) whenever a selected seal resolves an asset code, regardless
// of whether `seals` was passed as a prop -- so this file (which always
// passes seals={sampleSeals}) must mock these three too, or the
// unconditional Promise.all([getPMSchedules(), ...]) call throws
// "getPMSchedules is not a function".
vi.mock("../../../api/ai5rClient", () => ({
  postEngineeringAI: vi.fn(),
  getPMSchedules: vi.fn(),
  getCMReports: vi.fn(),
  getWorkOrders: vi.fn(),
}));

beforeEach(() => {
  getPMSchedules.mockResolvedValue([]);
  getCMReports.mockResolvedValue([]);
  getWorkOrders.mockResolvedValue([]);
});

// MWO-LTSA-036L: Seal.jsx no longer imports sampleSeals internally -- a
// real user never sees it (LTSAWorkspace.jsx renders <Seal /> with no
// `seals` prop, so the registry is genuinely empty). Every render(<Seal />)
// below now explicitly passes seals={sampleSeals} as a disclosed test
// fixture, exactly like any other test data -- this preserves full
// coverage of the real, working Engineering AI wiring (resolveAssetCode,
// postEngineeringAI request/response handling) without requiring any
// fabricated data to be visible in the actual application.

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SEAL_SOURCE = readFileSync(path.join(__dirname, "Seal.jsx"), "utf-8");
// MWO-LTSA-042A -- SealDetailPanel.jsx was deleted, replaced by
// SealOpenDesignView.jsx (the Open-Design-conformant detail view). This
// self-audit now reads the new canonical component's source instead.
const VIEW_SOURCE = readFileSync(
  path.join(__dirname, "..", "components", "SealOpenDesignView.jsx"),
  "utf-8"
);

const AI_RESPONSE = {
  summary: "Seal SC-001 is in service with no abnormal indications.",
  findings: ["No leak indications recorded in the last 30 days."],
  confidence: 0.81,
  evidence: [{ source: "ConditionMonitoringReading", reference: "CMON-2001" }],
  recommendations: ["Continue routine monitoring."],
  risk: "LOW",
  remaining_life: "240 days",
  provider: "CLAUDE",
  model: "claude-sonnet-5",
  latency: 0.615,
  token_usage: { input: 380, output: 84 },
  trace_id: "trace-seal-001",
  execution_status: "SUCCESS",
  source_references: [{ source: "ConditionMonitoringReading", reference: "CMON-2001" }],
  error: null,
};

afterEach(() => {
  vi.clearAllMocks();
});

async function renderAndSelect(code = "SC-001") {
  render(<Seal seals={sampleSeals} />);
  const seal = sampleSeals.find((item) => item.code === code);
  fireEvent.click(screen.getByText(code));
  await screen.findByRole("heading", { name: seal.name });
}

describe("EngineeringAIRequest construction", () => {
  it("posts asset_code resolved from the seal's first compatible pump's tag", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].asset_code).toBe("211-P-1A");
  });

  it("resolves asset_code from the FIRST compatible pump when a seal has more than one", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    const seal = sampleSeals.find((item) => item.code === "SC-001");
    expect(seal.compatiblePumps.length).toBeGreaterThan(1);
    await renderAndSelect("SC-001");
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].asset_code).toBe("211-P-1A");
  });

  it("reuses the existing 'summary' intent -- no new Seal-specific intent invented", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].intent).toBe("summary");
  });

  it("reuses the existing 'summary' prompt_type -- no new Seal-specific prompt_type invented", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].prompt_type).toBe("summary");
  });

  it("posts a non-empty string trace_id", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    const { trace_id } = postEngineeringAI.mock.calls[0][0];
    expect(typeof trace_id).toBe("string");
    expect(trace_id.length).toBeGreaterThan(0);
  });

  it("posts workspace = 'seal'", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].workspace).toBe("seal");
  });

  it("does not send selected_record_id (not applicable/supported for a seal-level summary)", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].selected_record_id).toBeUndefined();
  });

  it("does not send a question field (no question UI exists)", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    expect(postEngineeringAI.mock.calls[0][0].question).toBeUndefined();
  });
});

describe("POST invocation", () => {
  it("calls postEngineeringAI exactly once for a single seal selection", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalledTimes(1));
  });

  it("does not call postEngineeringAI before any seal is selected", async () => {
    render(<Seal seals={sampleSeals} />);
    expect(postEngineeringAI).not.toHaveBeenCalled();
  });

  it("does not call postEngineeringAI when the selected seal has no compatible pump", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    const seal = sampleSeals.find((item) => item.compatiblePumps.length === 0);
    expect(seal).toBeTruthy();
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText(seal.code));
    await screen.findByRole("heading", { name: seal.name });
    expect(postEngineeringAI).not.toHaveBeenCalled();
  });

  it("re-fetches with a fresh trace_id when a different seal is selected", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    render(<Seal seals={sampleSeals} />);

    fireEvent.click(screen.getByText("SC-001"));
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalledTimes(1));
    const firstTraceId = postEngineeringAI.mock.calls[0][0].trace_id;

    fireEvent.click(screen.getByText("SC-003"));
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalledTimes(2));
    const secondCall = postEngineeringAI.mock.calls[1][0];

    expect(secondCall.asset_code).toBe("305-P-2");
    expect(secondCall.trace_id).not.toBe(firstTraceId);
  });
});

describe("Response rendering", () => {
  it("renders the response summary", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    expect(await screen.findByText(AI_RESPONSE.summary)).toBeTruthy();
  });

  it("renders execution_status as the status badge", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    expect(await screen.findByText("SUCCESS")).toBeTruthy();
  });

  it("renders provider metadata", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    expect(await screen.findByText("CLAUDE")).toBeTruthy();
  });

  it("renders latency formatted in milliseconds", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    expect(await screen.findByText("615 ms")).toBeTruthy();
  });

  it("renders trace_id from the response", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    expect(await screen.findByText("trace-seal-001")).toBeTruthy();
  });

  it("renders confidence as a rounded percentage", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    expect(await screen.findByText("81%")).toBeTruthy();
  });

  it("renders risk", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    expect(await screen.findByText("LOW")).toBeTruthy();
  });

  it("renders remaining_life", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    expect(await screen.findByText("240 days")).toBeTruthy();
  });

  it("renders findings via the packaged EngineeringAIFindings component", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    expect(await screen.findByText(AI_RESPONSE.findings[0])).toBeTruthy();
    expect(await screen.findByRole("heading", { name: "Engineering Findings" })).toBeTruthy();
  });

  it("renders evidence via the packaged EngineeringAIEvidence component", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    const heading = await screen.findByRole("heading", { name: "Evidence Strip" });
    expect(heading.closest("section").textContent).toContain("CMON-2001");
  });

  it("renders recommendations via the packaged EngineeringAIRecommendation component", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    // "Recommendation" is now also the Inspector Rail's own section title
    // (<h3 class="rail-title">Recommendation</h3>) alongside the packaged
    // EngineeringAIRecommendation component's own heading -- findAllByRole,
    // not findByRole.
    expect((await screen.findAllByRole("heading", { name: "Recommendation" })).length).toBeGreaterThan(0);
    expect(await screen.findByText(AI_RESPONSE.recommendations[0])).toBeTruthy();
  });

  it("renders source references via the packaged EngineeringAISourceReferences component", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    expect(await screen.findByRole("heading", { name: "Source References" })).toBeTruthy();
  });
});

describe("Loading state (reuses the Failure Analysis / Pump model)", () => {
  it("shows a generating message while the AI request is in flight", async () => {
    let resolvePromise;
    postEngineeringAI.mockReturnValue(new Promise((resolve) => { resolvePromise = resolve; }));
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("SC-001"));

    expect(await screen.findByText("Generating seal summary…")).toBeTruthy();
    resolvePromise(AI_RESPONSE);
    await waitFor(() => expect(screen.getByText(AI_RESPONSE.summary)).toBeTruthy());
  });

  it("shows a Generating… status label while loading", async () => {
    let resolvePromise;
    postEngineeringAI.mockReturnValue(new Promise((resolve) => { resolvePromise = resolve; }));
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("SC-001"));

    expect(await screen.findByText("Generating…")).toBeTruthy();
    resolvePromise(AI_RESPONSE);
  });
});

describe("Retry (Golden Reference has none -- faithfully not replicated)", () => {
  it("Seal Workspace has no retry button or retry state", () => {
    expect(SEAL_SOURCE.toLowerCase()).not.toMatch(/retry/);
    expect(VIEW_SOURCE.toLowerCase()).not.toMatch(/retry/);
  });

  it("Golden Reference (FailureAnalysisWorkspace) still has no retry to diverge from", () => {
    const goldenReferenceSource = readFileSync(
      path.join(__dirname, "FailureAnalysisWorkspace.jsx"),
      "utf-8"
    );
    expect(goldenReferenceSource.toLowerCase()).not.toMatch(/retry/);
  });
});

describe("Error state", () => {
  it("renders a network error message", async () => {
    postEngineeringAI.mockRejectedValue(new Error("Engineering AI API unavailable"));
    await renderAndSelect("SC-001");
    expect(await screen.findByText("Engineering AI API unavailable")).toBeTruthy();
  });

  it("renders an Error status label on network failure", async () => {
    postEngineeringAI.mockRejectedValue(new Error("boom"));
    await renderAndSelect("SC-001");
    expect(await screen.findByText("Error")).toBeTruthy();
  });

  it("falls back to a generic message when the rejected error has no message", async () => {
    postEngineeringAI.mockRejectedValue({});
    await renderAndSelect("SC-001");
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
    await renderAndSelect("SC-001");
    expect(await screen.findByText("Asset context could not be built")).toBeTruthy();
    expect(screen.queryByText(AI_RESPONSE.summary)).toBeNull();
  });

  it("does not render Findings/Evidence/Recommendation/SourceReferences panels on business error", async () => {
    postEngineeringAI.mockResolvedValue({ ...AI_RESPONSE, execution_status: "ERROR", error: "boom" });
    await renderAndSelect("SC-001");
    await screen.findByText("boom");
    expect(screen.queryByRole("heading", { name: "Engineering Findings" })).toBeNull();
  });
});

describe("No compatible pump (Seal-specific edge case)", () => {
  it("shows the short Coverage reason and a Required Action instead of the generic 'has not run yet' message", async () => {
    const seal = sampleSeals.find((item) => item.compatiblePumps.length === 0);
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText(seal.code));
    await screen.findByRole("heading", { name: seal.name });
    // MWO-LTSA-046 P1 -- Engineering AI's "Reason" now shows the short
    // coverageMeta.label ("Outside LTSA Contract") instead of the full
    // sentence when that's the real cause, plus a "Required Action" line --
    // same underlying meaning (no resolvable LTSA-covered asset), reworded.
    // "Outside LTSA Contract" also appears in the LTSA Coverage card and
    // Action Bar -- getAllByText, not getByText.
    expect(screen.getAllByText("Outside LTSA Contract").length).toBeGreaterThan(0);
    expect(
      await screen.findByText(/associate this seal with an ltsa-covered asset/i)
    ).toBeTruthy();
  });

  it("shows an Unavailable status label, not Error", async () => {
    const seal = sampleSeals.find((item) => item.compatiblePumps.length === 0);
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText(seal.code));
    await screen.findByRole("heading", { name: seal.name });
    // MWO-LTSA-047 -- "Unavailable" also appears as the LTSA Coverage
    // card's own bold lead-in label above its capability list --
    // findAllByText, not findByText.
    expect((await screen.findAllByText("Unavailable")).length).toBeGreaterThan(0);
    expect(screen.queryByText("Error")).toBeNull();
  });
});

describe("Trace propagation", () => {
  it("renders the exact same trace_id the request sent, once the response echoes it back", async () => {
    postEngineeringAI.mockImplementation((request) =>
      Promise.resolve({ ...AI_RESPONSE, trace_id: request.trace_id })
    );
    await renderAndSelect("SC-001");
    await waitFor(() => expect(postEngineeringAI).toHaveBeenCalled());
    const sentTraceId = postEngineeringAI.mock.calls[0][0].trace_id;
    expect(await screen.findByText(sentTraceId)).toBeTruthy();
  });
});

describe("Regression: existing Seal Workspace behavior is unchanged", () => {
  it("still renders the page header", () => {
    render(<Seal seals={sampleSeals} />);
    expect(screen.getByRole("heading", { name: "Seal Workspace" })).toBeTruthy();
  });

  it("still renders all 10 sample seals in the registry table", () => {
    render(<Seal seals={sampleSeals} />);
    sampleSeals.forEach((seal) => {
      expect(screen.getByText(seal.code)).toBeTruthy();
    });
  });

  it("still shows the empty state before any seal is selected", () => {
    render(<Seal seals={sampleSeals} />);
    expect(screen.getByText(/no seal selected/i)).toBeTruthy();
  });

  it("still filters the registry table by search text", () => {
    render(<Seal seals={sampleSeals} />);
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "AESSEAL" } });
    expect(screen.getByText("SC-005")).toBeTruthy();
    expect(screen.queryByText("SC-001")).toBeNull();
  });

  it("still filters the registry table by status", () => {
    render(<Seal seals={sampleSeals} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "FAULT" } });
    expect(screen.getByText("SC-007")).toBeTruthy();
    expect(screen.queryByText("SC-001")).toBeNull();
  });

  it("still renders the seal's recommendation alongside the Engineering AI section", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    const seal = sampleSeals.find((item) => item.code === "SC-001");
    // seal.recommendation legitimately appears twice in the Open Design
    // layout (Recommended Replacement headline + Inspector Rail's
    // Recommendation section) -- getAllByText, not getByText.
    expect(screen.getAllByText(seal.recommendation).length).toBeGreaterThan(0);
    // "Engineering AI" is a section eyebrow label (<span class="eyebrow">),
    // not a heading, in the Open Design layout.
    expect(screen.getByText("Engineering AI")).toBeTruthy();
  });

  it("still renders compatible pumps and compatible seals as badges", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    await renderAndSelect("SC-001");
    expect(screen.getByText("PMP-001")).toBeTruthy();
  });
});

describe("Snapshot", () => {
  it("matches the SealOpenDesignView Engineering AI section snapshot when ready", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    const { container } = render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("SC-001"));
    await screen.findByText(AI_RESPONSE.summary);

    expect(container.querySelector(".seal-workspace-detail")).toMatchSnapshot();
  });
});

describe("Self-audit: only postEngineeringAI is used, no duplication, no forbidden objects", () => {
  it("Seal.jsx makes no raw fetch() call", () => {
    expect(SEAL_SOURCE).not.toMatch(/\bfetch\(/);
  });

  it("SealOpenDesignView.jsx makes no raw fetch() call", () => {
    expect(VIEW_SOURCE).not.toMatch(/\bfetch\(/);
  });

  function importLines(source) {
    return source.split("\n").filter((line) => line.trim().startsWith("import "));
  }

  it("Seal.jsx never imports AI_RUNTIME/Router/EngineeringAIClient/PromptBuilder/ContextEngine", () => {
    const lines = importLines(SEAL_SOURCE);
    for (const forbidden of ["AI_RUNTIME", "EngineeringAIClient", "EngineeringPromptBuilder", "EngineeringContextEngine"]) {
      expect(lines.some((line) => line.includes(forbidden))).toBe(false);
    }
  });

  it("SealOpenDesignView.jsx never imports AI_RUNTIME/Router/EngineeringAIClient/PromptBuilder/ContextEngine", () => {
    const lines = importLines(VIEW_SOURCE);
    for (const forbidden of ["AI_RUNTIME", "EngineeringAIClient", "EngineeringPromptBuilder", "EngineeringContextEngine"]) {
      expect(lines.some((line) => line.includes(forbidden))).toBe(false);
    }
  });

  it("does not define any forbidden Seal*-prefixed AI object", () => {
    for (const forbidden of [
      "SealAIClient",
      "SealPromptBuilder",
      "SealContextEngine",
      "SealGateway",
      "SealRuntime",
      "SealProvider",
      "SealRecommendationEngine",
      "SealResponseParser",
    ]) {
      expect(SEAL_SOURCE).not.toMatch(new RegExp(forbidden));
      expect(VIEW_SOURCE).not.toMatch(new RegExp(forbidden));
    }
  });

  it("does not redefine formatConfidence/formatLatency/formatValue/renderAIItem locally (no duplicate formatter)", () => {
    for (const helper of ["formatConfidence", "formatLatency", "formatValue", "renderAIItem"]) {
      const localDefinition = new RegExp(`(function|const)\\s+${helper}\\s*[=(]`);
      expect(SEAL_SOURCE).not.toMatch(localDefinition);
      expect(VIEW_SOURCE).not.toMatch(localDefinition);
    }
  });

  it("imports Engineering AI components only from the canonical package, never a direct component file", () => {
    expect(VIEW_SOURCE).toMatch(/from ["']\.\/engineering-ai["']/);
    expect(VIEW_SOURCE).not.toMatch(/from ["'][./]*components\/EngineeringAI\w+["']/);
  });

  it("SealOpenDesignView renders only packaged Engineering AI components for response content -- no inline field access on aiResponse beyond passing it through", () => {
    for (const field of ["aiResponse.summary", "aiResponse.findings", "aiResponse.confidence", "aiResponse.risk", "aiResponse.remaining_life", "aiResponse.evidence", "aiResponse.recommendations", "aiResponse.source_references"]) {
      expect(VIEW_SOURCE).not.toContain(field);
    }
  });

  it("uses the shared generateTraceId, not a locally re-implemented UUID/trace generator", () => {
    expect(SEAL_SOURCE).toMatch(/import generateTraceId from ["']\.\.\/utils\/generateTraceId["']/);
    expect(SEAL_SOURCE).not.toMatch(/crypto\.randomUUID/);
  });

  it("does not clear the previous seal's AI response as raw JSON on the screen while a new one loads", async () => {
    postEngineeringAI.mockResolvedValue(AI_RESPONSE);
    render(<Seal seals={sampleSeals} />);
    fireEvent.click(screen.getByText("SC-001"));
    await screen.findByText(AI_RESPONSE.summary);

    let resolveSecond;
    postEngineeringAI.mockReturnValue(new Promise((resolve) => { resolveSecond = resolve; }));
    fireEvent.click(screen.getByText("SC-003"));

    await waitFor(() => expect(screen.queryByText(AI_RESPONSE.summary)).toBeNull());
    expect(screen.getByText("Generating seal summary…")).toBeTruthy();
    resolveSecond({ ...AI_RESPONSE, summary: "Different seal summary." });
  });

  it("SealOpenDesignView never JSON-serializes the raw response as visible text (only packaged components format it)", () => {
    expect(VIEW_SOURCE).not.toMatch(/JSON\.stringify\(\s*aiResponse\s*\)/);
  });

  it("Seal.jsx does not construct any AI client, provider, or Router instance", () => {
    expect(SEAL_SOURCE).not.toMatch(/new\s+\w*(Client|Provider|Router)\(/);
  });

  it("Seal.jsx does not import samplePumps' tag as a duplicate of an already-canonical resolver (local, disclosed cross-reference only)", () => {
    expect(SEAL_SOURCE).toMatch(/samplePumps/);
    expect(SEAL_SOURCE).not.toMatch(/getPumps\(/);
  });
});
