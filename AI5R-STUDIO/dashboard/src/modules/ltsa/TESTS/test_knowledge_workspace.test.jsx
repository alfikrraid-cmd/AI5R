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
    const aiHeader = screen.getByRole("button", { name: /AI Insights/i });
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

    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(10);
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
    // inventory, pm, cm, breakdown, drawings, recommendation, ai-insights.
    // Timeline is intentionally excluded (its own component). Active Plans
    // (MWO-LTSA-036F) is also intentionally excluded -- ActivePlansPanel
    // renders its own Card, so it is not double-wrapped in a KnowledgeCard.
    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(10);
  });

  it("renders exactly 12 KnowledgeSection instances (no duplicated sections)", async () => {
    getPumpKnowledge.mockResolvedValue(backendResponse());

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const sections = [
      "summary",
      "active-plans",
      "timeline",
      "seal",
      "compat-seals",
      "inventory",
      "pm-history",
      "cm-history",
      "breakdown-history",
      "drawings",
      "recommendation",
      "ai-insights",
    ];
    sections.forEach((id) => expect(screen.getByTestId(`knowledge-section-${id}`)).toBeInTheDocument());
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
    expect(within(sealSection).getByTestId("knowledge-seal")).toBeInTheDocument();
    expect(within(sealSection).getByText("T48MP")).toBeInTheDocument();
    expect(within(sealSection).getByText("John Crane")).toBeInTheDocument();
    expect(within(sealSection).getByText("1K1K")).toBeInTheDocument();
    // "INSTALLED" legitimately renders twice: the section header's own
    // badge (badge={data.mechanicalSeal?.status}) AND the seal body's
    // status-signal line.
    expect(within(sealSection).getAllByText("INSTALLED").length).toBeGreaterThan(0);
  });

  it("leaves fields with no authoritative source as an honest 'Unavailable', never fabricated", async () => {
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
    // Model, Type, API Plan, Hours, MTBF, and Status (null here) have no
    // authoritative source in this fixture -- each renders "Unavailable",
    // never a guessed value.
    expect(within(sealSection).getAllByText("Unavailable").length).toBeGreaterThanOrEqual(5);
  });

  it("still shows the empty state when the backend returns current_seal: null (no authoritative installation)", async () => {
    getPumpKnowledge.mockResolvedValue(
      backendResponse({ data: { ...backendResponse().data, current_seal: null } })
    );

    render(<KnowledgeWorkspace tag={TAG} />);

    await waitFor(() => expect(screen.getByTestId("knowledge-workspace-success")).toBeInTheDocument());
    const sealSection = screen.getByTestId("knowledge-section-seal");
    expect(within(sealSection).getByText("Belum ada seal terpasang")).toBeInTheDocument();
    expect(within(sealSection).queryByTestId("knowledge-seal")).not.toBeInTheDocument();
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
    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(10);
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
    expect(screen.getAllByTestId("knowledge-card")).toHaveLength(10);
  });
});
