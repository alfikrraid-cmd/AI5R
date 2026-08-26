import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import KnowledgeWorkspace from "../pages/KnowledgeWorkspace";
import KnowledgeSection from "../components/KnowledgeSection";
import KnowledgeCard from "../components/KnowledgeCard";
import KnowledgeTimeline from "../components/KnowledgeTimeline";
import KnowledgeAIInsight from "../components/KnowledgeAIInsight";
import KnowledgeDrawingSection from "../components/KnowledgeDrawingSection";
import { getPumpKnowledge } from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({
  getPumpKnowledge: vi.fn(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

const TAG = "641-P-5";

function backendResponse(overrides = {}) {
  return {
    success: true,
    tag_number: TAG,
    data: {
      summary: {
        asset: { tag_number: TAG, pump_name: "Main Feed Pump", manufacturer: "Sulzer", model: "AB12", status: "normal" },
        pm_summary: { last_pm: null, status: "ACTIVE", overdue: false },
        cm_summary: { overall_condition: "NORMAL", leak_flag: false, latest_abnormal_values: null },
        seal_summary: { installed_seal: null, compatibility: [], stock_availability: "OK" },
        inventory_summary: { available: [], missing_critical_parts: [] },
        workorder_summary: { open_count: 0, highest_priority: null, newest_work_order: null },
        engineering_flags: [],
        evidence: [],
        metadata: { generated_at: "2026-08-06T00:00:00Z", asset_code: TAG, context_version: "1.0.0" },
      },
      timeline: [
        {
          id: "PM:PM-1",
          event_type: "PM",
          occurred_at: "2026-06-01",
          title: "PM Occurrence PM-1",
          description: null,
          severity: "UNKNOWN",
          source: "PM_OCCURRENCE",
          derived: true,
          payload: { pm_occurrence_code: "PM-1" },
        },
      ],
      seal: [{ seal_code: "SC-001", part_name: "John Crane Type 21" }],
      inventory: [{ stock_pool_id: "MSSP-001", seal_type: "T48MP", application_size: '3-1/2"', quantity_on_hand: 4, quantity_available: 4, verification_status: "CONFIRMED", stock_location: "Warehouse A" }],
      pm: [{ pm_occurrence_code: "PM-1", asset_code: TAG, occurrence_date: "2026-06-01" }],
      cm: [{ cm_report_code: "CM-1", asset_code: TAG, created_at: "2026-06-05", severity: "MINOR" }],
      breakdown: [{ maintenance_record_code: "MH-1", asset_code: TAG, performed_at: "2026-06-03", action_taken: "Replaced bearing" }],
      drawings: null,
      recommendation: null,
      pm_schedules: [],
      condition_monitoring_schedules: [],
    },
    ...overrides,
  };
}

describe("KnowledgeWorkspace render", () => {
  it("renders the equipment tag and name on success", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    // TAG and the pump name each legitimately render twice: the rail's
    // header (.eyebrow / h2.rail-title) AND the Equipment Summary card's
    // own Tag/Name fields.
    expect(screen.getAllByText(TAG).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Main Feed Pump").length).toBeGreaterThan(0);
  });

  it("calls the Knowledge API exactly once with the tag, no other API", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(getPumpKnowledge).toHaveBeenCalledTimes(1));
    expect(getPumpKnowledge).toHaveBeenCalledWith(TAG);
  });
});

describe("Loading state", () => {
  it("shows a skeleton while the API call is in flight", () => {
    getPumpKnowledge.mockReturnValue(new Promise(() => {}));

    render(<KnowledgeWorkspace tag={TAG} />);

    expect(screen.getByTestId("knowledge-workspace-loading")).toBeInTheDocument();
  });
});

describe("Error state", () => {
  it("shows an error card with a retry action when the API call fails", async () => {
    getPumpKnowledge.mockRejectedValue(new Error("Pump knowledge API unavailable"));

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-error")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Coba Lagi/i })).toBeInTheDocument();
  });

  it("retries the API call when Coba Lagi is clicked", async () => {
    getPumpKnowledge.mockRejectedValueOnce(new Error("boom")).mockResolvedValueOnce(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-error")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /Coba Lagi/i }));

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(getPumpKnowledge).toHaveBeenCalledTimes(2);
  });
});

describe("Empty state", () => {
  it("shows the whole-panel empty state when no tag is provided", () => {
    render(<KnowledgeWorkspace tag={null} />);

    expect(screen.getByTestId("knowledge-workspace-empty")).toBeInTheDocument();
    expect(getPumpKnowledge).not.toHaveBeenCalled();
  });

  it("shows a per-section empty state when drawings is empty", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const drawingsSection = screen.getByTestId("knowledge-section-drawings");
    expect(drawingsSection.querySelector(".eng-empty")).toBeInTheDocument();
  });

  it("shows a per-section empty state for Recommendation when null", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const recSection = screen.getByTestId("knowledge-section-recommendation");
    expect(recSection.querySelector(".eng-empty")).toBeInTheDocument();
  });
});

describe("KnowledgeSection collapse", () => {
  it("defaults open and toggles aria-expanded / DOM visibility on click", () => {
    render(
      <KnowledgeSection id="test-section" title="Test Section" badge="3">
        <p>section body content</p>
      </KnowledgeSection>
    );

    const header = screen.getByRole("button", { name: /Test Section/i });
    expect(header).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(header);
    expect(header).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(header);
    expect(header).toHaveAttribute("aria-expanded", "true");
  });

  it("respects defaultOpen={false}", () => {
    render(
      <KnowledgeSection id="closed-section" title="Closed Section" defaultOpen={false}>
        <p>hidden content</p>
      </KnowledgeSection>
    );

    expect(screen.getByRole("button", { name: /Closed Section/i })).toHaveAttribute("aria-expanded", "false");
  });

  it("renders the badge as real text content", () => {
    render(
      <KnowledgeSection id="badge-section" title="Badged" badge="Segera Hadir">
        <p>body</p>
      </KnowledgeSection>
    );

    expect(screen.getByText("Segera Hadir")).toBeInTheDocument();
  });
});

describe("KnowledgeCard variants", () => {
  it.each(["grid", "kv", "row-list", "prose"])("renders the %s variant with the correct data-variant attribute", (variant) => {
    render(<KnowledgeCard variant={variant}>content</KnowledgeCard>);

    expect(screen.getByTestId("knowledge-card")).toHaveAttribute("data-variant", variant);
  });

  it("applies the locked class when locked is true", () => {
    render(
      <KnowledgeCard variant="prose" locked>
        content
      </KnowledgeCard>
    );

    expect(screen.getByTestId("knowledge-card")).toHaveClass("locked");
  });
});

describe("Timeline render", () => {
  it("renders one .t-item per timeline event with tag, title, and time", () => {
    const items = [
      { id: "PM:PM-1", kind: "pm", title: "PM Occurrence PM-1", time: "2026-06-01", desc: null },
      { id: "CM:CM-1", kind: "cm", title: "CM Report CM-1", time: "2026-06-05", desc: "Seal leak" },
    ];

    render(<KnowledgeTimeline items={items} />);

    const timeline = screen.getByTestId("knowledge-timeline");
    expect(timeline.querySelectorAll(".t-item")).toHaveLength(2);
    expect(screen.getByText("PM Occurrence PM-1")).toBeInTheDocument();
    expect(screen.getByText("Seal leak")).toBeInTheDocument();
  });

  it("renders an empty state when there are no events", () => {
    render(<KnowledgeTimeline items={[]} />);

    expect(screen.queryByTestId("knowledge-timeline")).not.toBeInTheDocument();
  });
});

describe("API success -- data flows from the single Knowledge API into every section", () => {
  it("populates Stock V1 availability and PM/CM/Breakdown History from one response", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());

    expect(screen.getByText(/T48MP · 3-1\/2"/)).toBeInTheDocument();
    expect(screen.getByText("4 sets available")).toBeInTheDocument();
    expect(screen.getByText("Seal Stock Available")).toBeInTheDocument();
    expect(screen.queryByText("Compatible Seals")).not.toBeInTheDocument();
    expect(screen.queryByText("Inventory")).not.toBeInTheDocument();
    expect(screen.queryByText("Belum ada data inventaris")).not.toBeInTheDocument();
    expect(screen.getAllByText(/PM-1/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/CM-1/).length).toBeGreaterThan(0);
    // action_taken is appended to the performed_at meta line, not its own
    // text node -- match by substring.
    expect(screen.getByText((text) => text.includes("Replaced bearing"))).toBeInTheDocument();
  });

  it("renders unknown and zero Stock V1 quantities without converting between them", async () => {
    const response = backendResponse();
    response.data.inventory = [
      { stock_pool_id: "MSSP-UNKNOWN", seal_type: "T48MP", application_size: '3-1/2"', quantity_on_hand: null, quantity_available: null, verification_status: "UNKNOWN" },
      { stock_pool_id: "MSSP-ZERO", seal_type: "T6014DP", application_size: "60 mm", quantity_on_hand: 0, quantity_available: 0, verification_status: "CONFIRMED" },
    ];
    getPumpKnowledge.mockResolvedValue(response);

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(screen.getByText("Stock quantity unknown")).toBeInTheDocument();
    expect(screen.getByText("Out of Stock")).toBeInTheDocument();
  });
});

describe("Recommendation panel (MWO-LTSA-032B) -- bound to RecommendationEngine's real shape", () => {
  it("renders the empty state when the backend returns recommendation: null (today's live shape)", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(screen.getByText("Belum ada rekomendasi")).toBeInTheDocument();
  });

  it("renders priority/confidence/evidence/action once the backend serializes RecommendationEngine's list shape", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          recommendation: [
            {
              id: `REC_CRITICAL_CM:${TAG}`,
              rule_code: "REC_CRITICAL_CM",
              priority: 100,
              category: "INSPECTION",
              title: "Immediate Inspection",
              description: "An open Corrective Maintenance report with critical or major severity was found.",
              evidence: [{ source: "CMReport", reference: "CM-1", field: "severity", value: "CRITICAL" }],
              confidence: 1.0,
              action: "Dispatch a technician for immediate inspection.",
            },
          ],
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(screen.getByTestId("knowledge-recommendation-item")).toBeInTheDocument();
    expect(screen.getByText("Immediate Inspection")).toBeInTheDocument();
    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText("Dispatch a technician for immediate inspection.")).toBeInTheDocument();
    expect(screen.getAllByText("100%").length).toBeGreaterThan(0);
  });
});

describe("Responsive layout", () => {
  it("mounts the panel inside the reused .workspace-grid / .pump-workspace-root shell", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    const { container } = render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(container.querySelector(".pump-workspace-root")).toBeInTheDocument();
    expect(container.querySelector(".inspector-rail")).toBeInTheDocument();
  });

  // MWO-LTSA-ASSET360-UI-PRODUCTION-HARDENING-001 -- desktop layout
  // regression. jsdom does not compute real box widths, so this proves
  // the responsible class/grid architecture is actually applied (the
  // same .workspace-grid/.object-column/.inspector-rail classes
  // MaintenanceHistory.css already defines a real desktop grid-template-
  // columns and a 980px collapse breakpoint for) rather than measuring
  // pixels -- see the MWO report's "Responsive verification" item for
  // the code-level CSS evidence (grid-template-columns: minmax(0,1fr)
  // 336px; @media max-width:980px collapses to 1fr) this class
  // architecture activates.
  it("renders the main content column and the sidebar rail as siblings inside .workspace-grid (the fix for the narrow-desktop-column defect)", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    const { container } = render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const grid = container.querySelector(".workspace-grid");
    expect(grid).toBeInTheDocument();
    const objectColumn = grid.querySelector(":scope > .object-column");
    const inspectorRail = grid.querySelector(":scope > .inspector-rail");
    expect(objectColumn).toBeInTheDocument();
    expect(inspectorRail).toBeInTheDocument();
    // The success container itself is the grid, not a bare .inspector-rail
    // wrapping the whole page (the prior defect).
    expect(screen.getByTestId("knowledge-workspace-success")).toHaveClass("workspace-grid");
  });

  it("keeps Mechanical Seal, Stock V1, and Drawings in the sidebar rail; everything else in the main column", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    const { container } = render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const inspectorRail = container.querySelector(".inspector-rail");
    const objectColumn = container.querySelector(".object-column");

    ["seal", "stock-v1", "drawings"].forEach((id) => {
      expect(inspectorRail.querySelector(`[data-testid="knowledge-section-${id}"]`)).toBeInTheDocument();
    });
    [
      "summary",
      "active-plans",
      "timeline",
      "condition",
      "maintenance",
      "pm-history",
      "cm-history",
      "breakdown-history",
      "recommendation",
      "ai-insights",
      "work-orders",
      "ai-copilot",
    ].forEach((id) => {
      expect(objectColumn.querySelector(`[data-testid="knowledge-section-${id}"]`)).toBeInTheDocument();
    });
  });
});

describe("AI placeholder", () => {
  it("KnowledgeAIInsight always renders the locked state with a disabled CTA and no fabricated numbers", () => {
    render(<KnowledgeAIInsight />);

    expect(screen.getByText("Segera Hadir")).toBeInTheDocument();
    const cta = screen.getByRole("button", { name: /Belum Tersedia/i });
    expect(cta).toBeDisabled();
    expect(cta).toHaveAttribute("aria-disabled", "true");
    expect(screen.getAllByText("—").length).toBe(5);
  });

  it("AI Insights section defaults to collapsed in the full workspace", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    // MWO-LTSA-ASSET360-CONSOLIDATION-001 -- relabeled "AI Insights" ->
    // "AI Engineering Summary" (Section B), distinct from the new
    // interactive "AI Engineering Copilot" (Section J) below it; the
    // section id ("ai-insights") and its underlying deterministic engine
    // are unchanged.
    const aiHeader = screen.getByRole("button", { name: /AI Engineering Summary/i });
    expect(aiHeader).toHaveAttribute("aria-expanded", "false");
  });
});

describe("AI Insight (MWO-LTSA-035) -- deterministic, backed by EngineeringInsight", () => {
  it("renders the real Root Cause/Risk/Recommended Action/Confidence once the backend serializes ai_insight", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          ai_insight: {
            root_cause: "An open Corrective Maintenance report with critical or major severity was found.",
            risk: "CRITICAL",
            recommended_action: "Dispatch a technician for immediate inspection.",
            confidence: 1.0,
          },
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(screen.getByTestId("knowledge-ai-insight-real")).toBeInTheDocument();
    expect(
      screen.getByText("An open Corrective Maintenance report with critical or major severity was found.")
    ).toBeInTheDocument();
    expect(screen.getByText("Dispatch a technician for immediate inspection.")).toBeInTheDocument();
    expect(screen.queryByText("Segera Hadir")).not.toBeInTheDocument();
  });

  it("still shows the locked placeholder when the backend returns ai_insight: null (today's default, no recommendations)", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(screen.getByTestId("knowledge-ai-insight")).toBeInTheDocument();
  });
});

describe("Refresh -- MWO-LTSA-032A-R1", () => {
  it("shows a Refresh action in the success state, distinct from Retry", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(screen.getByTestId("knowledge-workspace-refresh")).toBeInTheDocument();
  });

  it("re-fetches on Refresh click, bypassing the controller cache (manual reload)", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(getPumpKnowledge).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId("knowledge-workspace-refresh"));

    await waitFor(() => expect(getPumpKnowledge).toHaveBeenCalledTimes(2));
    expect(getPumpKnowledge).toHaveBeenCalledWith(TAG);
  });

  it("Refresh does not change the rendered section/card counts (no duplication)", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("knowledge-workspace-refresh"));
    await waitFor(() => expect(getPumpKnowledge).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());

    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(8);
  });

  it("exposes Refresh as an accessible, named button (role + accessible name)", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Muat ulang data peralatan" })).toBeInTheDocument();
  });
});

describe("Drawing Viewer Integration (MWO-LTSA-034)", () => {
  const DRAWING_A = {
    id: "SED-1",
    title: "P-204A General Arrangement",
    documentNumber: "DWG-204A-001",
    revision: "C",
    status: "APPROVED",
    uploadedAt: "2026-05-01",
  };
  const DRAWING_B = {
    id: "SED-2",
    title: "P-204A Seal Chamber Detail",
    documentNumber: "DWG-204A-002",
    revision: "A",
    status: "DRAFT",
    uploadedAt: "2026-07-10",
  };

  it("renders the empty state when there are no drawings", () => {
    render(<KnowledgeDrawingSection items={[]} />);

    expect(screen.getByText("Belum ada gambar teknik")).toBeInTheDocument();
  });

  it("renders one row per drawing for multiple drawings", () => {
    render(<KnowledgeDrawingSection items={[DRAWING_A, DRAWING_B]} />);

    expect(screen.getAllByTestId("knowledge-drawing-item")).toHaveLength(2);
  });

  it("displays the drawing title", () => {
    render(<KnowledgeDrawingSection items={[DRAWING_A]} />);

    expect(screen.getByText("P-204A General Arrangement")).toBeInTheDocument();
  });

  it("displays the document number", () => {
    render(<KnowledgeDrawingSection items={[DRAWING_A]} />);

    expect(screen.getByTestId("knowledge-drawing-document-number")).toHaveTextContent("DWG-204A-001");
  });

  it("displays the revision", () => {
    render(<KnowledgeDrawingSection items={[DRAWING_A]} />);

    expect(screen.getByTestId("knowledge-drawing-revision")).toHaveTextContent("C");
  });

  it("displays the status", () => {
    render(<KnowledgeDrawingSection items={[DRAWING_A]} />);

    expect(screen.getByTestId("knowledge-drawing-status")).toHaveTextContent("APPROVED");
  });

  it("displays the uploaded date", () => {
    render(<KnowledgeDrawingSection items={[DRAWING_A]} />);

    expect(screen.getByTestId("knowledge-drawing-uploaded")).toHaveTextContent("2026-05-01");
  });

  it("shows a Viewer button for each drawing, no CAD/PDF rendering", () => {
    render(<KnowledgeDrawingSection items={[DRAWING_A, DRAWING_B]} />);

    expect(screen.getAllByRole("button", { name: /Buka Viewer/i })).toHaveLength(2);
  });

  it("flows real drawing metadata from the Knowledge API through KnowledgeWorkspace end-to-end", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          drawings: [
            {
              drawing_id: "SED-1",
              title: "P-204A General Arrangement",
              document_number: "DWG-204A-001",
              revision: "C",
              status: "APPROVED",
              file_name: "p-204a-ga.pdf",
              uploaded_at: "2026-05-01",
            },
          ],
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const drawingsSection = screen.getByTestId("knowledge-section-drawings");
    expect(within(drawingsSection).getByText("P-204A General Arrangement")).toBeInTheDocument();
    expect(within(drawingsSection).getByTestId("knowledge-drawing-revision")).toHaveTextContent("C");
    expect(within(drawingsSection).getByTestId("knowledge-drawing-status")).toHaveTextContent("APPROVED");
    expect(within(drawingsSection).getByRole("button", { name: /Buka Viewer/i })).toBeInTheDocument();
  });
});

describe("Reuse verification", () => {
  it("does not call any API other than getPumpKnowledge", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());
    const client = await import("../../../api/ai5rClient");
    const otherKeys = Object.keys(client).filter((key) => key !== "getPumpKnowledge");

    render(<KnowledgeWorkspace tag={TAG} />);
    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());

    // Every other export on the mocked client module must remain untouched --
    // proves the workspace consumes exactly one API, per the mission's
    // "Consume ONLY GET /api/ltsa/pumps/{tag}/knowledge" requirement.
    expect(otherKeys).toEqual([]);
  });

  it("renders exactly one KnowledgeCard per card-bodied section (no duplicated cards)", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    // 9 KnowledgeCard-bodied sections: summary, seal, compat-seals,
    // inventory, cm, breakdown, drawings, recommendation, ai-insights.
    // Timeline is intentionally excluded (its own component). Active Plans
    // (MWO-LTSA-036F) is also intentionally excluded -- ActivePlansPanel
    // renders its own Card, so it is not double-wrapped in a KnowledgeCard.
    // MWO-LTSA-ASSET360-CONSOLIDATION-001 -- pm-history was reduced from
    // 10 to 9: it now renders KnowledgePmHistorySection directly (its own
    // per-row expand/collapse, reusing PMOccurrenceDetailPanel) rather
    // than a single KnowledgeCard-wrapped RefRows list.
    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(8);
  });

  // MWO-LTSA-ASSET360-CONSOLIDATION-001 -- 4 new sections added: condition
  // (C), maintenance (D, Unified History), work-orders (H), ai-copilot (J).
  it("renders exactly 16 KnowledgeSection instances (no duplicated sections)", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const sections = [
      "summary",
      "active-plans",
      "timeline",
      "condition",
      "maintenance",
      "seal",
      "compat-seals",
      "stock-v1",
      "pm-history",
      "cm-history",
      "breakdown-history",
      "drawings",
      "recommendation",
      "ai-insights",
      "work-orders",
      "ai-copilot",
    ];
    sections.forEach((id) => expect(screen.getByTestId(`knowledge-section-${id}`)).toBeInTheDocument());
    expect(screen.getAllByTestId(/^knowledge-section-/)).toHaveLength(sections.length);
  });
});

describe("Active Plans Integration (MWO-LTSA-036F) -- pm_schedules / condition_monitoring_schedules, additive keys on the one Knowledge API response", () => {
  it("shows the empty state when both schedule lists are empty", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const activePlansSection = screen.getByTestId("knowledge-section-active-plans");
    expect(within(activePlansSection).getByText(/no active plans/i)).toBeInTheDocument();
  });

  it("renders PM Schedule rows, mapped through the same mapPMScheduleRecord PM.jsx itself uses", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          pm_schedules: [
            {
              pm_schedule_code: "PM-2001",
              asset_code: TAG,
              procedure: "Lubrication Check",
              frequency: "MONTHLY",
              next_due: "2026-08-01",
              status: "ACTIVE",
            },
          ],
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const activePlansSection = screen.getByTestId("knowledge-section-active-plans");
    expect(within(activePlansSection).getByText("Lubrication Check")).toBeInTheDocument();
  });

  it("renders Condition Monitoring Schedule rows, unmapped, as ActivePlansPanel already consumed them", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          condition_monitoring_schedules: [
            { condition_monitoring_schedule_code: "CMON-SCHED-001", asset_code: TAG, frequency: "WEEKLY" },
          ],
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const activePlansSection = screen.getByTestId("knowledge-section-active-plans");
    expect(within(activePlansSection).getByText("CMON-SCHED-001")).toBeInTheDocument();
  });

  it("renders both PM and Condition Monitoring schedules together when both exist", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          pm_schedules: [
            {
              pm_schedule_code: "PM-2001",
              asset_code: TAG,
              procedure: "Lubrication Check",
              frequency: "MONTHLY",
              next_due: "2026-08-01",
              status: "ACTIVE",
            },
          ],
          condition_monitoring_schedules: [
            { condition_monitoring_schedule_code: "CMON-SCHED-001", asset_code: TAG, frequency: "WEEKLY" },
          ],
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const activePlansSection = screen.getByTestId("knowledge-section-active-plans");
    expect(within(activePlansSection).getByText("Lubrication Check")).toBeInTheDocument();
    expect(within(activePlansSection).getByText("CMON-SCHED-001")).toBeInTheDocument();
    expect(within(activePlansSection).getByText("2")).toBeInTheDocument();
  });

  it("does not introduce a second fetch -- still exactly one getPumpKnowledge call with populated schedules", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          pm_schedules: [
            {
              pm_schedule_code: "PM-2001",
              asset_code: TAG,
              procedure: "Lubrication Check",
              frequency: "MONTHLY",
              next_due: "2026-08-01",
              status: "ACTIVE",
            },
          ],
          condition_monitoring_schedules: [
            { condition_monitoring_schedule_code: "CMON-SCHED-001", asset_code: TAG, frequency: "WEEKLY" },
          ],
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(getPumpKnowledge).toHaveBeenCalledTimes(1);
  });
});

describe("Mechanical Seal (MWO-LTSA-ASSET360-MECHANICAL-SEAL-WIRING-001) -- current_seal, additive key on the one Knowledge API response", () => {
  it("renders the authoritative current seal (T48MP) from the single aggregate response", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          current_seal: {
            seal_code: "T48MP",
            seal_name: null,
            manufacturer: "John Crane",
            model: null,
            shaft_size: null,
            material: "1K1K",
            temperature_limit: null,
            pressure_limit: null,
            status: "INSTALLED",
            installation_code: "INSTL-001-2026",
            installed_at: "2026-01-06",
            source: "seal_registry",
          },
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const sealSection = screen.getByTestId("knowledge-section-seal");
    const currentGroup = within(sealSection).getByTestId("knowledge-seal-current");
    expect(within(currentGroup).getByText("T48MP")).toBeInTheDocument();
    expect(within(currentGroup).getByText("John Crane")).toBeInTheDocument();
    expect(within(currentGroup).getByText("1K1K")).toBeInTheDocument();
    // "INSTALLED" legitimately renders twice: the section header's own
    // badge (badge={data.mechanicalSeal?.status}) AND the seal body's
    // status-signal line.
    expect(within(sealSection).getAllByText("INSTALLED").length).toBeGreaterThan(0);
  });

  it("leaves current-installation fields with no authoritative source as an honest 'Unavailable', never fabricated", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          current_seal: {
            seal_code: "T48MP",
            seal_name: null,
            manufacturer: "John Crane",
            model: null,
            shaft_size: null,
            material: "1K1K",
            temperature_limit: null,
            pressure_limit: null,
            status: null,
            installation_code: "INSTL-001-2026",
            installed_at: "2026-01-06",
            source: "seal_registry",
          },
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const sealSection = screen.getByTestId("knowledge-section-seal");
    const currentGroup = within(sealSection).getByTestId("knowledge-seal-current");
    // Name/Model have no authoritative source in this fixture (seal_name/
    // model: null) -- each renders "Not recorded", never a guessed value.
    expect(within(currentGroup).getAllByText("Not recorded").length).toBeGreaterThanOrEqual(2);
  });

  it("current-installation fields fall back to 'Not recorded' (never inferred from configured seal type) when current_seal is null", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({ data: { ...backendResponse().data, current_seal: null } })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const sealSection = screen.getByTestId("knowledge-section-seal");
    const currentGroup = within(sealSection).getByTestId("knowledge-seal-current");
    expect(within(currentGroup).getAllByText("Not recorded").length).toBeGreaterThanOrEqual(6);
  });

  it("does not introduce a second fetch -- still exactly one getPumpKnowledge call", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          current_seal: { seal_code: "T48MP", manufacturer: "John Crane" },
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(getPumpKnowledge).toHaveBeenCalledTimes(1);
  });

  it("does not change the KnowledgeCard/KnowledgeSection counts (additive field, no new section)", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          current_seal: { seal_code: "T48MP", manufacturer: "John Crane" },
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(8);
  });
});

describe("Configured vs Current Seal (MWO-LTSA-ASSET360-SEAL-SEMANTICS-001) -- configured_seal (design data) stays distinct from current_seal (installation evidence)", () => {
  it("renders Configured Seal Type and API Plan from configured_seal, independent of current_seal", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          configured_seal: { seal_type: "T48MP", api_plan: "11/62" },
          current_seal: null,
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const sealSection = screen.getByTestId("knowledge-section-seal");
    const configuredGroup = within(sealSection).getByTestId("knowledge-seal-configured");
    expect(within(configuredGroup).getByText("T48MP")).toBeInTheDocument();
    expect(within(configuredGroup).getByText("11/62")).toBeInTheDocument();
  });

  it("shows the current-installation section as 'Not recorded' even when a configured seal type is known -- never inferred from seal_type", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          configured_seal: { seal_type: "T48MP", api_plan: "11/62" },
          current_seal: null,
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const sealSection = screen.getByTestId("knowledge-section-seal");
    const currentGroup = within(sealSection).getByTestId("knowledge-seal-current");
    expect(within(currentGroup).getAllByText("Not recorded").length).toBeGreaterThanOrEqual(1);
    // Never "T48MP" leaking into the current-installation group as if it
    // were installation evidence.
    expect(within(currentGroup).queryByText("T48MP")).not.toBeInTheDocument();
  });

  it.each([
    ["212-P-7B", "T48MP", null],
    ["110-P-10", "T48MP", "11/62"],
    ["140-P-11", "T48MP", "11/61"],
  ])(
    "%s: configured seal type/API plan render from configured_seal while current_seal stays 'Not recorded' (production evidence: installation_report has zero rows)",
    async (tag, sealType, apiPlan) => {
      getPumpKnowledge.mockResolvedValue(
        backendResponse({
          tag_number: tag,
          data: {
            ...backendResponse().data,
            summary: { ...backendResponse().data.summary, asset: { tag_number: tag, pump_name: "Pump" } },
            configured_seal: { seal_type: sealType, api_plan: apiPlan },
            current_seal: null,
          },
        })
      );

      render(<KnowledgeWorkspace tag={tag} />);

      await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
      const sealSection = screen.getByTestId("knowledge-section-seal");
      const configuredGroup = within(sealSection).getByTestId("knowledge-seal-configured");
      expect(within(configuredGroup).getByText(sealType)).toBeInTheDocument();
      if (apiPlan) {
        expect(within(configuredGroup).getByText(apiPlan)).toBeInTheDocument();
      }
      const currentGroup = within(sealSection).getByTestId("knowledge-seal-current");
      expect(within(currentGroup).getAllByText("Not recorded").length).toBeGreaterThanOrEqual(1);
    }
  );

  it("does not introduce a second fetch and does not change section/card counts", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          configured_seal: { seal_type: "T48MP", api_plan: "11/62" },
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(getPumpKnowledge).toHaveBeenCalledTimes(1);
    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(8);
  });
});

describe("Response envelope (MWO-LTSA-ASSET360-UI-PRODUCTION-HARDENING-001) -- proves the UI reads response.data, not the top-level object", () => {
  it("reads configured_seal/current_seal/pump from inside the real {success, tag_number, data} envelope, not from a flattened top level", async () => {
    // Deliberately mirrors the exact live production envelope shape,
    // including fields OUTSIDE `data` (success/tag_number) that must be
    // ignored by field-mapping -- a prior false-negative smoke test
    // looked at the top-level object instead of response.data and never
    // caught a wiring gap. getPumpKnowledge's own real implementation
    // returns this full envelope; KnowledgeWorkspaceController.load()
    // unwraps `.data` before this hook ever sees it.
    getPumpKnowledge.mockResolvedValue({
      success: true,
      tag_number: "212-P-7B",
      // Top-level decoys: if the mapping code ever regressed to reading
      // these instead of the nested equivalents inside `data`, the
      // assertions below would fail.
      configured_seal: { seal_type: "WRONG-TOP-LEVEL", api_plan: "WRONG" },
      current_seal: { seal_code: "WRONG-TOP-LEVEL" },
      data: {
        ...backendResponse().data,
        summary: { ...backendResponse().data.summary, asset: { tag_number: "212-P-7B", pump_name: "Pump" } },
        pump: { tag_number: "212-P-7B", area: "Reaktor", seal_type: "T48MP" },
        configured_seal: { seal_type: "T48MP", api_plan: null },
        current_seal: null,
      },
    });

    render(<KnowledgeWorkspace tag="212-P-7B" />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const sealSection = screen.getByTestId("knowledge-section-seal");
    const configuredGroup = within(sealSection).getByTestId("knowledge-seal-configured");
    expect(within(configuredGroup).getByText("T48MP")).toBeInTheDocument();
    expect(within(configuredGroup).queryByText("WRONG-TOP-LEVEL")).not.toBeInTheDocument();
    const summarySection = screen.getByTestId("knowledge-summary");
    expect(within(summarySection).getByText("Reaktor")).toBeInTheDocument();
  });
});

describe("Equipment Summary (MWO-LTSA-ASSET360-UI-PRODUCTION-HARDENING-001) -- honest area/location/status/condition/timestamp semantics", () => {
  function knowledgeFor(tag, pump) {
    return backendResponse({
      tag_number: tag,
      data: {
        ...backendResponse().data,
        summary: { ...backendResponse().data.summary, asset: { tag_number: tag, pump_name: "Pump" } },
        pump,
      },
    });
  }

  it("212-P-7B: renders the canonical tag and real Area (Reaktor) while Location stays honestly Unavailable (null)", async () => {
    getPumpKnowledge.mockResolvedValue(
      knowledgeFor("212-P-7B", {
        tag_number: "212-P-7B",
        area: "Reaktor",
        location: null,
        pump_type: "OH2",
        api_plan: null,
        seal_type: "T48MP",
        status: "UNKNOWN",
      })
    );

    render(<KnowledgeWorkspace tag="212-P-7B" />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const summary = screen.getByTestId("knowledge-summary");
    expect(within(summary).getByText("212-P-7B")).toBeInTheDocument();
    expect(within(summary).getByText("Reaktor")).toBeInTheDocument();
    expect(within(summary).getByText("OH2")).toBeInTheDocument();
  });

  it("does not conflate Asset Status (master data) with Condition (health assessment) -- both render distinctly when both are known", async () => {
    getPumpKnowledge.mockResolvedValue(
      knowledgeFor("212-P-7B", { tag_number: "212-P-7B", status: "UNKNOWN" })
    );

    render(<KnowledgeWorkspace tag="212-P-7B" />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const summary = screen.getByTestId("knowledge-summary");
    // Asset Status: UNKNOWN (ltsa_pumps.status, master data) --
    // Condition: normal (cm_summary.overall_condition, health assessment,
    // fixture default NORMAL) -- both real, both visible, never collapsed
    // into one ambiguous "Status" field that would have to pick a winner.
    expect(within(summary).getByText("UNKNOWN")).toBeInTheDocument();
    expect(within(summary).getByText("normal")).toBeInTheDocument();
  });

  it("Location is never fabricated from Area when Location is genuinely null", async () => {
    getPumpKnowledge.mockResolvedValue(
      knowledgeFor("212-P-7B", { tag_number: "212-P-7B", area: "Reaktor", location: null })
    );

    render(<KnowledgeWorkspace tag="212-P-7B" />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const summary = screen.getByTestId("knowledge-summary");
    const locationField = within(summary).getByText("Location").closest(".eng-summary-field");
    expect(within(locationField).getByText("Unavailable")).toBeInTheDocument();
    // Area, a real and different field, is not hidden just because
    // Location is absent.
    expect(within(summary).getByText("Reaktor")).toBeInTheDocument();
  });

  it("formats a valid ISO timestamp human-readably, under an honest 'Generated At' label (not 'Last Updated')", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          summary: {
            ...backendResponse().data.summary,
            metadata: { ...backendResponse().data.summary.metadata, generated_at: "2026-08-22T03:45:31.972633+00:00" },
          },
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const summary = screen.getByTestId("knowledge-summary");
    expect(within(summary).getByText("Generated At")).toBeInTheDocument();
    expect(within(summary).queryByText("2026-08-22T03:45:31.972633+00:00")).not.toBeInTheDocument();
    expect(within(summary).queryByText(/Last Updated/i)).not.toBeInTheDocument();
    // Human-readable: day, short month, year, hour:minute -- never the raw
    // ISO string dumped into the card.
    expect(within(summary).getByText(/22 Aug 2026/)).toBeInTheDocument();
  });

  it("renders honestly when the timestamp is null", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          summary: {
            ...backendResponse().data.summary,
            metadata: { ...backendResponse().data.summary.metadata, generated_at: null },
          },
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(screen.getByTestId("knowledge-summary")).toBeInTheDocument();
  });

  it("does not crash on a malformed timestamp -- falls back honestly instead of rendering garbage", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({
        data: {
          ...backendResponse().data,
          summary: {
            ...backendResponse().data.summary,
            metadata: { ...backendResponse().data.summary.metadata, generated_at: "not-a-real-timestamp" },
          },
        },
      })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(screen.getByTestId("knowledge-summary")).toBeInTheDocument();
    expect(screen.queryByText("not-a-real-timestamp")).not.toBeInTheDocument();
  });

  it.each([
    ["212-P-7B", "T48MP", null, "Reaktor"],
    ["110-P-10", "T48MP", "11/62", undefined],
    ["140-P-11", "T48MP", "11/61", undefined],
  ])("%s: Equipment Summary reflects production-evidenced pump master data", async (tag, sealType, apiPlan, area) => {
    getPumpKnowledge.mockResolvedValue(
      knowledgeFor(tag, { tag_number: tag, area, seal_type: sealType, api_plan: apiPlan, status: "UNKNOWN" })
    );

    render(<KnowledgeWorkspace tag={tag} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const summary = screen.getByTestId("knowledge-summary");
    expect(within(summary).getByText(tag)).toBeInTheDocument();
    expect(within(summary).getByText("UNKNOWN")).toBeInTheDocument();
    if (area) {
      expect(within(summary).getByText(area)).toBeInTheDocument();
    }
  });
});

describe("Application chrome via WorkspaceShell (MWO-LTSA-036I)", () => {
  it("shows the breadcrumb once a tag resolves to real content", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    const { container } = render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const crumb = container.querySelector(".crumb");
    expect(crumb).toBeInTheDocument();
    expect(crumb).toHaveTextContent("Asset 360");
    expect(crumb).toHaveTextContent(TAG);
  });

  it("shows a theme toggle button that flips data-theme when clicked", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    const { container } = render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const root = container.querySelector(".pump-workspace-root");
    const before = root.getAttribute("data-theme");

    fireEvent.click(screen.getByRole("button", { name: /toggle theme/i }));

    expect(root.getAttribute("data-theme")).not.toBe(before);
  });

  it("shows the Command Palette Actions trigger and opens the palette on click", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    const { container } = render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /actions/i }));

    expect(container.querySelector(".cmdk-overlay")).toHaveAttribute("data-open", "true");
  });

  it("does not show any chrome when no tag is provided (mirrors MaintenanceHistory's own no-chrome-until-selected precedent)", () => {
    render(<KnowledgeWorkspace tag={null} />);

    expect(screen.getByTestId("knowledge-workspace-empty")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /toggle theme/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /actions/i })).not.toBeInTheDocument();
  });

  it("does not change the KnowledgeCard/KnowledgeSection counts (chrome is outside the rail, no duplication)", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(8);
  });
});
