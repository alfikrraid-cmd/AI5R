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
});
