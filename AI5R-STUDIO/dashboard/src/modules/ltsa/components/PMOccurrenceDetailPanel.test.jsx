import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PMOccurrenceDetailPanel from "./PMOccurrenceDetailPanel";
import { getPMCMEvidence } from "../../../api/ai5rClient";

// MWO-LTSA-PM-CM-REVIEW-UI-001 -- PMOccurrenceDetailPanel embeds the real
// EvidenceAttachments widget, which fetches getPMCMEvidence on mount, so
// every test here must mock it (same reasoning as
// ConditionMonitoring.test.jsx's own updated header comment).
vi.mock("../../../api/ai5rClient", () => ({
  getPMCMEvidence: vi.fn(),
  uploadPMCMEvidence: vi.fn(),
  pmCMEvidenceDownloadUrl: vi.fn((id) => `https://example.test/evidence/${id}`),
}));

beforeEach(() => {
  getPMCMEvidence.mockResolvedValue([]);
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

function baseOccurrence(overrides = {}) {
  return {
    id: "PMOCC-1",
    pmScheduleCode: "PM-2001",
    equipmentTag: "211-P-1A",
    occurrenceDate: "2026-08-01",
    activities: [{ code: "1", description: "Flushing Line", side: null, done: true }],
    finding: null,
    preliminaryRecommendation: null,
    remarks: null,
    workflowStatus: "DRAFT",
    returnReason: null,
    technicalOutcome: null,
    technicalComment: null,
    technicalRecommendation: null,
    createdBy: "creator-uuid",
    createdAt: "2026-08-01T09:00:00Z",
    updatedBy: "creator-uuid",
    updatedAt: "2026-08-01T09:00:00Z",
    submittedBy: null,
    submittedAt: null,
    reviewedBy: null,
    reviewedAt: null,
    technicalReviewedBy: null,
    technicalReviewedAt: null,
    ...overrides,
  };
}

describe("PMOccurrenceDetailPanel", () => {
  it("shows an empty state when no occurrence is selected", () => {
    render(<PMOccurrenceDetailPanel occurrence={null} />);

    expect(screen.getByText(/no pm occurrence selected/i)).toBeTruthy();
  });

  it("renders the workflow status badge and honest empty states for finding/recommendation", async () => {
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence()} canWrite={false} />);

    expect(screen.getByText("DRAFT")).toBeTruthy();
    expect(screen.getByText("No field recommendation recorded.")).toBeTruthy();
    expect(screen.getByText("No technical recommendation yet.")).toBeTruthy();
    await screen.findByText("No evidence attached.");
  });

  it("shows Field Recommendation and Technical Recommendation as visually separate cards, never merged", async () => {
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({
          workflowStatus: "FINALIZED",
          technicalOutcome: "TECHNICALLY_APPROVED",
          preliminaryRecommendation: "Replace seal within 2 weeks (TAP field call).",
          technicalRecommendation: "Approved -- schedule replacement in next shutdown window.",
        })}
      />
    );

    expect(await screen.findByText("Replace seal within 2 weeks (TAP field call).")).toBeTruthy();
    expect(screen.getByText("Approved -- schedule replacement in next shutdown window.")).toBeTruthy();
    expect(screen.getByText("Field Recommendation — TAP Engineer")).toBeTruthy();
    expect(screen.getByText("Technical Recommendation — John Crane Engineer")).toBeTruthy();
    expect(screen.getByText("Technically Approved")).toBeTruthy();
  });

  it("prominently shows the return reason and re-enables editing when RETURNED_FOR_CORRECTION", async () => {
    const onSaveDraft = vi.fn().mockResolvedValue();
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({ workflowStatus: "RETURNED_FOR_CORRECTION", returnReason: "Missing DE-side reading." })}
        canWrite
        onSaveDraft={onSaveDraft}
      />
    );

    expect(await screen.findByText(/Reason: Missing DE-side reading\./)).toBeTruthy();
    expect(screen.getByLabelText("Finding")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Save Draft" })).toBeTruthy();
  });

  it("TAP Engineer (canWrite): can edit a DRAFT occurrence and save the draft", async () => {
    const onSaveDraft = vi.fn().mockResolvedValue();
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence()} canWrite onSaveDraft={onSaveDraft} />);

    fireEvent.change(await screen.findByLabelText("Finding"), { target: { value: "Minor leak observed at DE side." } });
    fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

    await waitFor(() => {
      expect(onSaveDraft).toHaveBeenCalledWith(
        "PMOCC-1",
        expect.objectContaining({ finding: "Minor leak observed at DE side." })
      );
    });
  });

  it("TAP Engineer (canWrite): can submit a DRAFT occurrence", async () => {
    const onSubmit = vi.fn().mockResolvedValue();
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence()} canWrite onSubmit={onSubmit} />);

    fireEvent.click(await screen.findByRole("button", { name: "Submit" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("PMOCC-1"));
  });

  it("TAP Engineer without write permission never sees edit controls or Actions card", async () => {
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence()} canWrite={false} />);

    await screen.findByText("No evidence attached.");
    expect(screen.queryByLabelText("Finding")).toBeNull();
    expect(screen.queryByRole("button", { name: "Save Draft" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Submit" })).toBeNull();
  });

  it("SUBMITTED + no review permission: read-only, no silent mutation, honest waiting state", async () => {
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence({ workflowStatus: "SUBMITTED" })} canWrite />);

    expect(screen.getByText(/Submitted and awaiting review/)).toBeTruthy();
    expect(screen.queryByLabelText("Finding")).toBeNull();
    expect(screen.queryByRole("button", { name: "Save Draft" })).toBeNull();
  });

  it("TAP Admin: sees Return for Correction on a SUBMITTED record, requires a reason, never sees Acknowledge/Technically Approve", async () => {
    const onAdminReturn = vi.fn().mockResolvedValue();
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({ workflowStatus: "SUBMITTED" })}
        canAdminReview
        onAdminReturn={onAdminReturn}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Return for Correction" }));
    expect(await screen.findByText("A return reason is required.")).toBeTruthy();
    expect(onAdminReturn).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Return reason"), { target: { value: "Please recheck flushing line." } });
    fireEvent.click(screen.getByRole("button", { name: "Return for Correction" }));

    expect(onAdminReturn).toHaveBeenCalledWith("PMOCC-1", "Please recheck flushing line.");
    expect(screen.queryByRole("button", { name: "Acknowledge" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Technically Approve" })).toBeNull();
  });

  it("John Crane: Return for Correction requires a comment before calling onTechnicalReview", async () => {
    const onTechnicalReview = vi.fn().mockResolvedValue();
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({ workflowStatus: "SUBMITTED" })}
        canTechnicalReview
        onTechnicalReview={onTechnicalReview}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Return for Correction" }));
    expect(await screen.findByText("A comment is required to return for correction.")).toBeTruthy();
    expect(onTechnicalReview).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Technical comment"), { target: { value: "Needs a clearer reading." } });
    fireEvent.click(screen.getByRole("button", { name: "Return for Correction" }));

    await waitFor(() => {
      expect(onTechnicalReview).toHaveBeenCalledWith(
        "PMOCC-1",
        expect.objectContaining({ action: "RETURN", comment: "Needs a clearer reading." })
      );
    });
  });

  it("John Crane: Technically Approve calls onTechnicalReview with action APPROVE, no comment required", async () => {
    const onTechnicalReview = vi.fn().mockResolvedValue();
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({ workflowStatus: "SUBMITTED" })}
        canTechnicalReview
        onTechnicalReview={onTechnicalReview}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Technically Approve" }));

    await waitFor(() => {
      expect(onTechnicalReview).toHaveBeenCalledWith("PMOCC-1", expect.objectContaining({ action: "APPROVE" }));
    });
  });

  it("John Crane: Acknowledge calls onTechnicalReview with action ACKNOWLEDGE", async () => {
    const onTechnicalReview = vi.fn().mockResolvedValue();
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({ workflowStatus: "SUBMITTED" })}
        canTechnicalReview
        onTechnicalReview={onTechnicalReview}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Acknowledge" }));

    await waitFor(() => {
      expect(onTechnicalReview).toHaveBeenCalledWith("PMOCC-1", expect.objectContaining({ action: "ACKNOWLEDGE" }));
    });
  });

  it("John Crane never sees TAP field-edit controls (no impersonation)", async () => {
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence({ workflowStatus: "SUBMITTED" })} canTechnicalReview />);

    await screen.findByText("John Crane Technical Review");
    expect(screen.queryByLabelText("Finding")).toBeNull();
    expect(screen.queryByRole("button", { name: "Save Draft" })).toBeNull();
  });

  it("Pertamina (no write/review permission): fully read-only, no evidence upload, no review controls", async () => {
    render(
      <PMOccurrenceDetailPanel occurrence={baseOccurrence({ workflowStatus: "SUBMITTED" })} canWrite={false} canAdminReview={false} canTechnicalReview={false} />
    );

    await screen.findByText("No evidence attached.");
    expect(screen.queryByTestId("evidence-file-input")).toBeNull();
    expect(screen.queryByRole("button", { name: "Return for Correction" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Save Draft" })).toBeNull();
  });

  it("shows attribution (actor + timestamp) honestly for created/submitted/reviewed", () => {
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({
          submittedBy: "tap-eng-uuid",
          submittedAt: "2026-08-02T10:00:00Z",
        })}
      />
    );

    expect(screen.getByText("tap-eng-uuid · 2026-08-02T10:00:00Z")).toBeTruthy();
  });

  // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001
  it("shows Source Workbook/Sheet/Row for a historically-imported occurrence", () => {
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({
          sourceWorkbookName: "CM & PM Summary HOC JUNI.xlsx",
          sourceSheetName: " PM Mech Seal",
          sourceRowNumber: 23,
        })}
      />
    );

    expect(screen.getByText("Source Workbook")).toBeTruthy();
    expect(screen.getByText("CM & PM Summary HOC JUNI.xlsx")).toBeTruthy();
    expect(screen.getByText("Source Sheet")).toBeTruthy();
    expect(screen.getByText("PM Mech Seal")).toBeTruthy();
    expect(screen.getByText("Source Row")).toBeTruthy();
    expect(screen.getByText("23")).toBeTruthy();
  });

  it("shows N/A for Source Workbook/Sheet/Row, never fabricated, for a live-entered occurrence", () => {
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence()} />);

    const naValues = screen.getAllByText("N/A");
    expect(naValues.length).toBe(3);
  });

  // MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- "UNSCHEDULED::<workbook>" is
  // source-workbook provenance, never a real operational schedule; must
  // never be presented under the "PM Schedule" label.
  it("never presents UNSCHEDULED::<workbook> as the PM Schedule for a historical import with no real schedule", () => {
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({
          pmScheduleCode: "UNSCHEDULED::Laporan PM, CM & Pemasangan Seal HCC JANUARI 2026.xlsx",
          sourceWorkbookName: "Laporan PM, CM & Pemasangan Seal HCC JANUARI 2026.xlsx",
        })}
      />
    );

    expect(screen.queryByText(/UNSCHEDULED::/)).toBeNull();
    expect(screen.getByText(/no linked schedule/i)).toBeTruthy();
    // Provenance is preserved, unmodified, in the Source card.
    expect(screen.getByText("Laporan PM, CM & Pemasangan Seal HCC JANUARI 2026.xlsx")).toBeTruthy();
  });

  it("still presents a real pm_schedule_code as the PM Schedule value", () => {
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence({ pmScheduleCode: "PM-2001" })} />);

    expect(screen.getByText("PM-2001")).toBeTruthy();
  });
});

// MWO-LTSA-HISTORICAL-PM-ACTIVITY-DISPLAY-001 -- a historical
// (provenance=HISTORICAL_IMPORT) occurrence renders its activities
// directly from the stored array, never merged with/padded out by the
// fixed ACTIVITY_OPTIONS checklist, and never requiring a `code` field
// (confirmed: real historical entries only ever carry
// {description, done}).
describe("PMOccurrenceDetailPanel -- historical activities display (MWO-LTSA-HISTORICAL-PM-ACTIVITY-DISPLAY-001)", () => {
  it("1: renders exactly the done=true historical entries, nothing else", () => {
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({
          provenance: "HISTORICAL_IMPORT",
          activities: [
            { done: true, description: "Flushing Line" },
            { done: true, description: "Quench Line" },
          ],
        })}
      />
    );

    expect(screen.getByText("Activities Performed")).toBeTruthy();
    expect(screen.getByText(/Flushing Line/)).toBeTruthy();
    expect(screen.getByText(/Quench Line/)).toBeTruthy();
    // none of the other ACTIVITY_OPTIONS labels appear as performed --
    // this is the exact 110-P-8A / 2026-07-07 production example.
    expect(screen.queryByText(/Strainer/)).toBeNull();
    expect(screen.queryByText(/Check Valve DE Side/)).toBeNull();
    expect(screen.queryByText(/Check Valve NDE Side/)).toBeNull();
    expect(screen.queryByText(/Reservoir/)).toBeNull();
    expect(screen.queryByText(/Cooling Water Cooler/)).toBeNull();
    // never the interactive/generic checklist for a historical record.
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("2: renders correctly even though no entry carries a `code` field", () => {
    const activities = [{ done: true, description: "Flushing Line" }];
    expect(activities[0].code).toBeUndefined();
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence({ provenance: "HISTORICAL_IMPORT", activities })} />);

    expect(screen.getByText(/Flushing Line/)).toBeTruthy();
  });

  it("3: a DE/NDE-side variant outside ACTIVITY_OPTIONS renders verbatim, not dropped", () => {
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({
          provenance: "HISTORICAL_IMPORT",
          activities: [{ done: true, description: "Flushing Line DE Side" }],
        })}
      />
    );

    expect(screen.getByText(/Flushing Line DE Side/)).toBeTruthy();
  });

  it('4: renders "Resevoir" exactly as stored -- never silently corrected to "Reservoir"', () => {
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({
          provenance: "HISTORICAL_IMPORT",
          activities: [{ done: true, description: "Resevoir" }],
        })}
      />
    );

    expect(screen.getByText(/Resevoir/)).toBeTruthy();
    expect(screen.queryByText(/^Reservoir$/)).toBeNull();
  });

  it("5: zero performed activities shows the honest empty state, never an invented activity", () => {
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({ provenance: "HISTORICAL_IMPORT", activities: [] })}
      />
    );

    expect(screen.getByText("No maintenance activity recorded.")).toBeTruthy();
  });

  it("5b: entries present but none done=true also shows the empty state, never a checked mark", () => {
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({
          provenance: "HISTORICAL_IMPORT",
          activities: [{ done: false, description: "Flushing Line" }],
        })}
      />
    );

    expect(screen.getByText("No maintenance activity recorded.")).toBeTruthy();
  });

  it("6: a MANUAL (live digital) occurrence uses the grouped activity catalog, unchanged by the historical fix", () => {
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({
          provenance: "MANUAL",
          activities: [{ code: "1", description: "Flushing Line", side: null, done: true }],
        })}
      />
    );

    expect(screen.getByText("Activities")).toBeTruthy();
    expect(screen.queryByText("Activities Performed")).toBeNull();
    // MWO-LTSA-PM-ACTIVITY-TAXONOMY-001 -- the grouped 19-variant catalog
    // renders (7 families x General/DE/NDE where evidenced), including
    // unchecked options -- exactly the pre-existing "full catalog always
    // shown" behavior for a live digital PM, just a wider catalog now.
    expect(screen.getAllByRole("checkbox").length).toBe(19);
    expect(screen.getByText("Strainer")).toBeTruthy();
    expect(screen.getByText("Reservoir")).toBeTruthy();
  });

  it("6b: an occurrence with no provenance at all (existing pre-MWO fixtures) keeps using the grouped MANUAL catalog", () => {
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence()} />);

    expect(screen.getByText("Activities")).toBeTruthy();
    expect(screen.getAllByRole("checkbox").length).toBe(19);
  });

  it("historical Save Draft never rewrites activities from ACTIVITY_OPTIONS -- passes the original array through unchanged", async () => {
    const onSaveDraft = vi.fn().mockResolvedValue({});
    const historicalActivities = [{ done: true, description: "Flushing Line" }, { done: true, description: "Resevoir" }];
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({ provenance: "HISTORICAL_IMPORT", activities: historicalActivities })}
        canWrite
        onSaveDraft={onSaveDraft}
      />
    );

    fireEvent.click(screen.getByText("Save Draft"));
    await waitFor(() => expect(onSaveDraft).toHaveBeenCalled());
    expect(onSaveDraft.mock.calls[0][1].activities).toEqual(historicalActivities);
  });
});

// MWO-LTSA-PM-ACTIVITY-TAXONOMY-001 -- MANUAL-provenance activities now
// render via the shared grouped PMActivityFamilyChecklist; a MANUAL
// record's own legacy numeric codes (1/4/6/8/17/18/19, the only codes
// that ever existed before this MWO) must keep matching correctly
// against the expanded catalog with zero migration.
describe("PMOccurrenceDetailPanel -- grouped activity catalog for MANUAL PM (MWO-LTSA-PM-ACTIVITY-TAXONOMY-001)", () => {
  it("14: a legacy numeric-coded MANUAL record renders its checked activity correctly under the new catalog", async () => {
    render(
      <PMOccurrenceDetailPanel
        occurrence={baseOccurrence({
          activities: [{ code: "1", description: "Flushing Line", side: null, done: true }],
        })}
      />
    );
    expect((await screen.findByLabelText("Flushing Line")).checked).toBe(true);
    expect(screen.getByLabelText("Flushing Line DE Side").checked).toBe(false);
  });

  it("shows the grouped family catalog (not the old flat list) for a MANUAL/undefined-provenance record", async () => {
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence()} />);
    expect(await screen.findByText("Activities")).toBeTruthy();
    expect(screen.queryByText("Activities Performed")).toBeNull();
    expect(screen.getByTestId("activity-family-Cooler")).toBeTruthy();
    expect(screen.getByTestId("activity-family-Cooling Water Cooler")).toBeTruthy();
  });

  it("12: no history/ConMon/pump context auto-selects any activity -- editing a fresh DRAFT with zero activities leaves every checkbox unchecked", async () => {
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence({ activities: [] })} canWrite />);
    for (const box of await screen.findAllByRole("checkbox")) {
      expect(box.checked).toBe(false);
    }
  });

  it("13/16: saving a MANUAL record serializes new selections with the new stable string code, full catalog included", async () => {
    const onSaveDraft = vi.fn().mockResolvedValue({});
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence({ activities: [] })} canWrite onSaveDraft={onSaveDraft} />);

    fireEvent.click(await screen.findByLabelText("Cooler DE Side"));
    fireEvent.click(screen.getByText("Save Draft"));

    await waitFor(() => expect(onSaveDraft).toHaveBeenCalled());
    const payload = onSaveDraft.mock.calls[0][1].activities;
    expect(payload).toHaveLength(19); // full catalog, existing payload contract preserved
    expect(payload).toContainEqual({ code: "COOLER_DE", description: "Cooler DE Side", side: "DE", done: true });
  });

  it("5/6: DE and NDE (and General) of the same family can be selected together and both save correctly", async () => {
    const onSaveDraft = vi.fn().mockResolvedValue({});
    render(<PMOccurrenceDetailPanel occurrence={baseOccurrence({ activities: [] })} canWrite onSaveDraft={onSaveDraft} />);

    fireEvent.click(await screen.findByLabelText("Cooler"));
    fireEvent.click(screen.getByLabelText("Cooler DE Side"));
    fireEvent.click(screen.getByLabelText("Cooler NDE Side"));
    fireEvent.click(screen.getByText("Save Draft"));

    await waitFor(() => expect(onSaveDraft).toHaveBeenCalled());
    const done = onSaveDraft.mock.calls[0][1].activities.filter((a) => a.done).map((a) => a.code);
    expect(done.sort()).toEqual(["COOLER", "COOLER_DE", "COOLER_NDE"]);
  });
});
