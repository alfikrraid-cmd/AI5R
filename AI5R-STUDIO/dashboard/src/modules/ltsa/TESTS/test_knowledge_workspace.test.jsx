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
      inventory: [{ seal_code: "SC-001", quantity_on_hand: 4, reorder_point: 2, location: "Warehouse A" }],
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
  it("populates Compatible Seals, Inventory, PM/CM/Breakdown History from one response", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());

    // "John Crane Type 21" legitimately renders twice: Compatible Seals'
    // .part-name AND Inventory's .inv-name, both joined from the same
    // seal_code by useKnowledgeWorkspace's mapInventory().
    expect(screen.getAllByText("John Crane Type 21").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/PM-1/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/CM-1/).length).toBeGreaterThan(0);
    // action_taken is appended to the performed_at meta line, not its own
    // text node -- match by substring.
    expect(screen.getByText((text) => text.includes("Replaced bearing"))).toBeInTheDocument();
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

  it("keeps only Inventory, Drawings and Documents in the sidebar rail; Mechanical Seal (with Compatible Seals) and everything else in the main column", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    const { container } = render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const inspectorRail = container.querySelector(".inspector-rail");
    const objectColumn = container.querySelector(".object-column");

    ["inventory", "drawings", "documents"].forEach((id) => {
      expect(inspectorRail.querySelector(`[data-testid="knowledge-section-${id}"]`)).toBeInTheDocument();
    });
    // LTSA_ASSET360_CURRENT_INSTALLATION_AND_SERVICE_AGE_R1 -- no seal content left in the rail.
    expect(inspectorRail.querySelector('[data-testid="knowledge-section-seal"]')).toBeNull();
    expect(inspectorRail.querySelector('[data-testid="knowledge-seal"]')).toBeNull();
    expect(screen.queryByTestId("knowledge-section-compat-seals")).toBeNull();
    [
      "summary",
      "active-plans",
      "seal",
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

    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(9);
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
    // 10 KnowledgeCard-bodied sections: summary, seal, compat-seals,
    // inventory, cm, breakdown, drawings, documents, recommendation,
    // ai-insights. Timeline is intentionally excluded (its own component).
    // Active Plans (MWO-LTSA-036F) is also intentionally excluded --
    // ActivePlansPanel renders its own Card, so it is not double-wrapped in
    // a KnowledgeCard. MWO-LTSA-ASSET360-CONSOLIDATION-001 -- pm-history
    // was reduced from 10 to 9: it now renders KnowledgePmHistorySection
    // directly (its own per-row expand/collapse, reusing
    // PMOccurrenceDetailPanel) rather than a single KnowledgeCard-wrapped
    // RefRows list. MWO-LTSA-ASSET360-COMPLETENESS-FIX-021B -- a new
    // "documents" section (item B, distinct from drawings) brings this
    // back up to 10. LTSA_ASSET360_CURRENT_INSTALLATION_AND_SERVICE_AGE_R1 --
    // Compatible Seals moved inside the Mechanical Seal card: 9.
    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(9);
  });

  // MWO-LTSA-ASSET360-CONSOLIDATION-001 -- 4 new sections added: condition
  // (C), maintenance (D, Unified History), work-orders (H), ai-copilot (J).
  // MWO-LTSA-ASSET360-COMPLETENESS-FIX-021B -- 1 more added: documents
  // (item B, distinct from drawings, fixing the previously-mislabeled
  // Documents nav entry that pointed at the Drawings section).
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
      "inventory",
      "pm-history",
      "cm-history",
      "breakdown-history",
      "drawings",
      "documents",
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

describe("Mechanical Seal -- Current Installation (LTSA_ASSET360_CURRENT_INSTALLATION_AND_SERVICE_AGE_R1)", () => {
  const NOT_RECORDED_INSTALLATION = {
    installation_status: "NOT_RECORDED",
    installed_seal_type: null,
    installed_seal_unit: null,
    seal_code: null,
    installation_date: null,
    installation_position: null,
    source_document: null,
    source_installation_code: null,
    removed_at: null,
    time_since_installation_days: null,
    time_since_installation_hours: null,
    time_basis: "CALENDAR_TIME",
    time_precision: null,
    actual_operating_hours: null,
  };

  function installed(overrides = {}) {
    return {
      ...NOT_RECORDED_INSTALLATION,
      installation_status: "INSTALLED",
      installed_seal_type: "T8B1-RS",
      installation_date: "2026-05-22",
      source_document: "SCAN 033 INSTALLATION REPORT 211-P-1A.pdf",
      source_installation_code: "INSTL-033-2026",
      time_since_installation_days: 126,
      time_since_installation_hours: 3024,
      time_precision: "DATE_ONLY",
      ...overrides,
    };
  }

  function withSeal(tag, dataOverrides) {
    return backendResponse({
      tag_number: tag,
      data: {
        ...backendResponse().data,
        summary: { ...backendResponse().data.summary, asset: { tag_number: tag, pump_name: "Pump" } },
        ...dataOverrides,
      },
    });
  }

  function rowValue(group, label) {
    const row = within(group)
      .getAllByText(label)
      .map((element) => element.closest(".info-row"))
      .find(Boolean);
    return row.querySelector(".v").textContent;
  }

  async function renderSeal(tag, dataOverrides) {
    getPumpKnowledge.mockResolvedValue(withSeal(tag, dataOverrides));
    render(<KnowledgeWorkspace tag={tag} />);
    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    return screen.getByTestId("knowledge-section-seal");
  }

  it("701-P-1A: no installation evidence renders NOT RECORDED and never falls back to the configured seal or catalog status", async () => {
    const sealSection = await renderSeal("701-P-1A", {
      configured_seal: { seal_type: "T8B1", api_plan: "23/61" },
      // Decoy: a seal_registry catalog status must never read as installation status.
      current_seal: { seal_code: "T8B1", status: "INSTALLED" },
      current_installation: NOT_RECORDED_INSTALLATION,
      current_installations: [],
      installation_history: [],
    });

    const configured = within(sealSection).getByTestId("knowledge-seal-configured");
    expect(rowValue(configured, "Configured Seal")).toBe("T8B1");
    expect(rowValue(configured, "API Plan")).toBe("23/61");

    const current = within(sealSection).getByTestId("knowledge-seal-current");
    expect(rowValue(current, "Installation Status")).toBe("NOT RECORDED");
    expect(rowValue(current, "Installed Seal Type")).toBe("Not Recorded");
    expect(rowValue(current, "Installed Seal Unit")).toBe("Not Recorded");
    expect(rowValue(current, "Installation Date")).toBe("Not Recorded");
    expect(within(current).queryByText("T8B1")).toBeNull();
    expect(within(sealSection).queryByText("INSTALLED")).toBeNull();

    const time = within(sealSection).getByTestId("knowledge-seal-time");
    expect(rowValue(time, "Days Since Installation")).toBe("N/A");
    expect(rowValue(time, "Hours Since Installation")).toBe("N/A");
    expect(rowValue(within(sealSection).getByTestId("knowledge-seal-operating-hours"), "Actual Operating Hours")).toBe("N/A");
    expect(within(sealSection).getByText("No installation history recorded")).toBeInTheDocument();

    const kpis = screen.getByTestId("asset-header-kpis");
    expect(within(kpis).getByTestId("kpi-configured-seal")).toHaveTextContent("T8B1");
    expect(within(kpis).getByTestId("kpi-installed-seal")).toHaveTextContent("Not Recorded");
    expect(within(kpis).getByTestId("kpi-installed-seal")).toHaveTextContent("Installation Status: NOT RECORDED");
    expect(within(kpis).queryByText("Current Seal / Seal Status")).toBeNull();
  });

  it("211-P-1A: installed seal type differs from the configured seal and shows calendar-time service age", async () => {
    const sealSection = await renderSeal("211-P-1A", {
      configured_seal: { seal_type: "T8B1", api_plan: "23/61" },
      current_installation: installed(),
      current_installations: [installed()],
      installation_history: [
        {
          installation_code: "INSTL-033-2026",
          pump_tag_number: "211-P-1A",
          installation_date: "2026-05-22",
          time_precision: "DATE_ONLY",
          installation_position: null,
          installed_seal_type: "T8B1-RS",
          installed_seal_unit: null,
          seal_code: null,
          report_no: "033/INSTL/TAP/05-2026",
          source_document: "SCAN 033 INSTALLATION REPORT 211-P-1A.pdf",
        },
      ],
    });

    expect(rowValue(within(sealSection).getByTestId("knowledge-seal-configured"), "Configured Seal")).toBe("T8B1");
    const current = within(sealSection).getByTestId("knowledge-seal-current");
    expect(rowValue(current, "Installation Status")).toBe("INSTALLED");
    expect(rowValue(current, "Installed Seal Type")).toBe("T8B1-RS");
    expect(rowValue(current, "Installed Seal Unit")).toBe("Not Recorded");
    expect(rowValue(current, "Position")).toBe("Not Recorded");
    expect(rowValue(current, "Installation Date")).toBe("2026-05-22");
    expect(rowValue(current, "Source")).toBe("SCAN 033 INSTALLATION REPORT 211-P-1A.pdf");

    const time = within(sealSection).getByTestId("knowledge-seal-time");
    expect(rowValue(time, "Days Since Installation")).toBe("126 days");
    expect(rowValue(time, "Hours Since Installation")).toBe("3,024 hours");
    expect(rowValue(time, "Basis")).toBe("Calendar Time");
    expect(rowValue(time, "Precision")).toBe("Date only");
    expect(within(sealSection).queryByText(/running hours|operating hours since/i)).toBeNull();

    const history = within(sealSection).getByTestId("installation-history-INSTL-033-2026");
    expect(history).toHaveTextContent("2026-05-22");
    expect(history).toHaveTextContent("T8B1-RS");

    const kpi = within(screen.getByTestId("asset-header-kpis")).getByTestId("kpi-installed-seal");
    expect(kpi).toHaveTextContent("T8B1-RS");
    expect(kpi).toHaveTextContent("Installation Status: INSTALLED");
    expect(kpi).toHaveTextContent("Seal type only — no tracked seal unit");
  });

  it("renders one current installation per explicitly evidenced position", async () => {
    const de = installed({ installation_position: "DE", installed_seal_type: "DE-TYPE", source_installation_code: "INSTL-1" });
    const nde = installed({ installation_position: "NDE", installed_seal_type: "NDE-TYPE", source_installation_code: "INSTL-2" });
    const sealSection = await renderSeal("940-P-2A", {
      current_installation: de,
      current_installations: [de, nde],
      installation_history: [],
    });

    const entries = within(within(sealSection).getByTestId("knowledge-seal-current")).getAllByTestId("current-installation-entry");
    expect(entries).toHaveLength(2);
    expect(entries[0]).toHaveTextContent("DE-TYPE");
    expect(entries[1]).toHaveTextContent("NDE-TYPE");
    expect(within(entries[1]).getByText("Position").closest(".info-row")).toHaveTextContent("NDE");
  });

  it("a removed installation shows REMOVED and stops the counter", async () => {
    const removed = { ...NOT_RECORDED_INSTALLATION, installation_status: "REMOVED", removed_at: "2026-08-01", source_installation_code: "INSTL-033-2026" };
    const sealSection = await renderSeal("211-P-1A", {
      current_installation: removed,
      current_installations: [removed],
      installation_history: [],
    });

    const current = within(sealSection).getByTestId("knowledge-seal-current");
    expect(rowValue(current, "Installation Status")).toBe("REMOVED");
    expect(rowValue(current, "Removed")).toBe("2026-08-01");
    expect(rowValue(within(sealSection).getByTestId("knowledge-seal-time"), "Days Since Installation")).toBe("N/A");
  });

  it("places Mechanical Seal in the main column and leaves only Inventory, Drawings and Documents in the rail", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());
    const { container } = render(<KnowledgeWorkspace tag={TAG} />);
    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());

    const rail = container.querySelector(".inspector-rail");
    const main = container.querySelector(".object-column");
    expect(main.querySelector('[data-testid="knowledge-section-seal"]')).toBeInTheDocument();
    expect(rail.querySelector('[data-testid="knowledge-section-seal"]')).toBeNull();
    expect(rail.querySelector('[data-testid="knowledge-seal"]')).toBeNull();
    expect(screen.queryByTestId("knowledge-section-compat-seals")).toBeNull();
    expect(Array.from(rail.querySelectorAll('[data-testid^="knowledge-section-"]')).map((el) => el.dataset.testid)).toEqual([
      "knowledge-section-inventory",
      "knowledge-section-drawings",
      "knowledge-section-documents",
    ]);
  });

  it("keeps Compatible Seals inside the Mechanical Seal section and makes exactly one Knowledge API call", async () => {
    const sealSection = await renderSeal(TAG, {
      current_installation: installed(),
      current_installations: [installed()],
      installation_history: [],
    });

    expect(within(sealSection).getByTestId("knowledge-seal-compatible")).toBeInTheDocument();
    expect(getPumpKnowledge).toHaveBeenCalledTimes(1);
    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(9);
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

  it("shows the current-installation section as 'Not Recorded' even when a configured seal type is known -- never inferred from seal_type", async () => {
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
    expect(within(currentGroup).getAllByText("Not Recorded").length).toBeGreaterThanOrEqual(1);
    // Never "T48MP" leaking into the current-installation group as if it
    // were installation evidence.
    expect(within(currentGroup).queryByText("T48MP")).not.toBeInTheDocument();
  });

  it.each([
    ["212-P-7B", "T48MP", null],
    ["110-P-10", "T48MP", "11/62"],
    ["140-P-11", "T48MP", "11/61"],
  ])(
    "%s: configured seal type/API plan render from configured_seal while Current Installation stays 'Not Recorded' (no installation evidence)",
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
      expect(within(currentGroup).getAllByText("Not Recorded").length).toBeGreaterThanOrEqual(1);
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
    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(9);
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
    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(9);
  });
});
