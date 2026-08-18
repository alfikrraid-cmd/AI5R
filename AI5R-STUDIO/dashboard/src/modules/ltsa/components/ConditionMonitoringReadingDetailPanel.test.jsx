import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ConditionMonitoringReadingDetailPanel from "./ConditionMonitoringReadingDetailPanel";
import { getPMCMEvidence } from "../../../api/ai5rClient";

// MWO-LTSA-PM-CM-REVIEW-UI-001 -- extended panel embeds the real
// EvidenceAttachments widget, which fetches getPMCMEvidence on mount, so
// every test here must mock it (same reasoning as PMOccurrenceDetailPanel.
// test.jsx's own header comment).
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

function baseReading(overrides = {}) {
  return {
    id: "CMONR-1",
    scheduleCode: "CMON-SCHED-001",
    equipmentTag: "641-P-5",
    area: null,
    readingDate: "2026-08-01",
    mechsealTempDe: 84,
    mechsealTempNde: 79,
    leakDe: false,
    leakNde: false,
    pumpOperatingState: "RUNNING",
    finding: null,
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

describe("ConditionMonitoringReadingDetailPanel (MWO-LTSA-PM-CM-REVIEW-UI-001 extensions)", () => {
  it("shows an empty state when no reading is selected", () => {
    render(<ConditionMonitoringReadingDetailPanel reading={null} />);

    expect(screen.getByText(/no condition monitoring reading selected/i)).toBeTruthy();
  });

  it("renders the workflow status badge and honest empty states for finding/technical recommendation/evidence", async () => {
    render(<ConditionMonitoringReadingDetailPanel reading={baseReading()} canWrite={false} />);

    expect(screen.getByText("DRAFT")).toBeTruthy();
    expect(screen.getByText("No finding recorded.")).toBeTruthy();
    expect(screen.getByText("No technical recommendation yet.")).toBeTruthy();
    await screen.findByText("No evidence attached.");
  });

  it("prominently shows the return reason when RETURNED_FOR_CORRECTION", async () => {
    render(
      <ConditionMonitoringReadingDetailPanel
        reading={baseReading({ workflowStatus: "RETURNED_FOR_CORRECTION", returnReason: "Recheck mechseal temp DE." })}
        canWrite
      />
    );

    expect(await screen.findByText(/Reason: Recheck mechseal temp DE\./)).toBeTruthy();
    expect(screen.getByLabelText("Finding")).toBeTruthy();
  });

  it("TAP Engineer (canWrite): can edit and save the finding on a DRAFT reading, passing through existing measurements unmodified", async () => {
    const onSaveDraft = vi.fn().mockResolvedValue();
    render(<ConditionMonitoringReadingDetailPanel reading={baseReading()} canWrite onSaveDraft={onSaveDraft} />);

    fireEvent.change(await screen.findByLabelText("Finding"), { target: { value: "Slight vibration noted." } });
    fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

    await waitFor(() => {
      expect(onSaveDraft).toHaveBeenCalledWith(
        "CMONR-1",
        expect.objectContaining({
          finding: "Slight vibration noted.",
          measurements: expect.objectContaining({ mechseal_temp_de: 84, mechseal_temp_nde: 79 }),
        })
      );
    });
  });

  it("TAP Engineer (canWrite): can submit a DRAFT reading", async () => {
    const onSubmit = vi.fn().mockResolvedValue();
    render(<ConditionMonitoringReadingDetailPanel reading={baseReading()} canWrite onSubmit={onSubmit} />);

    fireEvent.click(await screen.findByRole("button", { name: "Submit" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("CMONR-1"));
  });

  it("without write permission, never shows edit controls or Actions card", async () => {
    render(<ConditionMonitoringReadingDetailPanel reading={baseReading()} canWrite={false} />);

    await screen.findByText("No evidence attached.");
    expect(screen.queryByLabelText("Finding")).toBeNull();
    expect(screen.queryByRole("button", { name: "Save Draft" })).toBeNull();
  });

  it("SUBMITTED + no review permission: read-only, honest waiting state, no silent mutation", async () => {
    render(<ConditionMonitoringReadingDetailPanel reading={baseReading({ workflowStatus: "SUBMITTED" })} canWrite />);

    expect(screen.getByText(/Submitted and awaiting review/)).toBeTruthy();
    expect(screen.queryByLabelText("Finding")).toBeNull();
  });

  it("TAP Admin: Return for Correction requires a reason, never sees Acknowledge/Technically Approve", async () => {
    const onAdminReturn = vi.fn().mockResolvedValue();
    render(
      <ConditionMonitoringReadingDetailPanel
        reading={baseReading({ workflowStatus: "SUBMITTED" })}
        canAdminReview
        onAdminReturn={onAdminReturn}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Return for Correction" }));
    expect(await screen.findByText("A return reason is required.")).toBeTruthy();
    expect(onAdminReturn).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Return reason"), { target: { value: "Please retake reading." } });
    fireEvent.click(screen.getByRole("button", { name: "Return for Correction" }));

    await waitFor(() => expect(onAdminReturn).toHaveBeenCalledWith("CMONR-1", "Please retake reading."));
    expect(screen.queryByRole("button", { name: "Acknowledge" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Technically Approve" })).toBeNull();
  });

  it("John Crane: Technically Approve calls onTechnicalReview with action APPROVE", async () => {
    const onTechnicalReview = vi.fn().mockResolvedValue();
    render(
      <ConditionMonitoringReadingDetailPanel
        reading={baseReading({ workflowStatus: "SUBMITTED" })}
        canTechnicalReview
        onTechnicalReview={onTechnicalReview}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Technically Approve" }));

    await waitFor(() => {
      expect(onTechnicalReview).toHaveBeenCalledWith("CMONR-1", expect.objectContaining({ action: "APPROVE" }));
    });
  });

  it("John Crane: Return for Correction requires a comment", async () => {
    const onTechnicalReview = vi.fn().mockResolvedValue();
    render(
      <ConditionMonitoringReadingDetailPanel
        reading={baseReading({ workflowStatus: "SUBMITTED" })}
        canTechnicalReview
        onTechnicalReview={onTechnicalReview}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Return for Correction" }));
    expect(await screen.findByText("A comment is required to return for correction.")).toBeTruthy();
    expect(onTechnicalReview).not.toHaveBeenCalled();
  });

  it("John Crane never sees TAP field-edit controls (no impersonation)", async () => {
    render(<ConditionMonitoringReadingDetailPanel reading={baseReading({ workflowStatus: "SUBMITTED" })} canTechnicalReview />);

    await screen.findByText("John Crane Technical Review");
    expect(screen.queryByLabelText("Finding")).toBeNull();
    expect(screen.queryByRole("button", { name: "Save Draft" })).toBeNull();
  });

  it("Pertamina (no write/review permission): fully read-only, no evidence upload, no review controls", async () => {
    render(
      <ConditionMonitoringReadingDetailPanel
        reading={baseReading({ workflowStatus: "SUBMITTED" })}
        canWrite={false}
        canAdminReview={false}
        canTechnicalReview={false}
      />
    );

    await screen.findByText("No evidence attached.");
    expect(screen.queryByTestId("evidence-file-input")).toBeNull();
    expect(screen.queryByRole("button", { name: "Return for Correction" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Save Draft" })).toBeNull();
  });

  it("shows attribution (actor + timestamp) honestly for submitted", () => {
    render(
      <ConditionMonitoringReadingDetailPanel
        reading={baseReading({ submittedBy: "tap-eng-uuid", submittedAt: "2026-08-02T10:00:00Z" })}
      />
    );

    expect(screen.getByText("tap-eng-uuid · 2026-08-02T10:00:00Z")).toBeTruthy();
  });

  it("technical_outcome renders as a separate badge from workflow_status, never merged", async () => {
    render(
      <ConditionMonitoringReadingDetailPanel
        reading={baseReading({ workflowStatus: "FINALIZED", technicalOutcome: "ACKNOWLEDGED" })}
      />
    );

    expect(screen.getByText("FINALIZED")).toBeTruthy();
    expect(screen.getByText("Acknowledged")).toBeTruthy();
  });
});
