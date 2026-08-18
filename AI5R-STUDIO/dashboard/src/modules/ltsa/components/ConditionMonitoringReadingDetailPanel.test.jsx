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

  // MWO-LTSA-PM-CM-REVIEW-PRE-PUSH-CLOSURE-001 -- golden migration-014
  // measurement entry, DRAFT and RETURNED_FOR_CORRECTION edit paths.
  describe("golden CMON measurement editing (Create + Edit parity)", () => {
    it("DRAFT: renders every migration-014 field as an editable input, pre-filled from the real record", async () => {
      const onSaveDraft = vi.fn().mockResolvedValue();
      render(
        <ConditionMonitoringReadingDetailPanel
          reading={baseReading({ bearingTempDe: 61, bearingTempNde: 58, motorCurrent: 22.1 })}
          canWrite
          onSaveDraft={onSaveDraft}
        />
      );

      expect(await screen.findByLabelText("Bearing Temp DE")).toHaveProperty("value", "61");
      expect(screen.getByLabelText("Bearing Temp NDE")).toHaveProperty("value", "58");
      expect(screen.getByLabelText("Motor Current")).toHaveProperty("value", "22.1");
    });

    it("DRAFT: saving sends null (not 0) for a measurement never entered", async () => {
      const onSaveDraft = vi.fn().mockResolvedValue();
      render(<ConditionMonitoringReadingDetailPanel reading={baseReading()} canWrite onSaveDraft={onSaveDraft} />);

      fireEvent.click(await screen.findByRole("button", { name: "Save Draft" }));

      await waitFor(() => expect(onSaveDraft).toHaveBeenCalled());
      const payload = onSaveDraft.mock.calls[0][1];
      expect(payload.measurements.suction_pressure).toBeNull();
      expect(payload.measurements.motor_current).toBeNull();
      expect(payload.measurements.bearing_temp_de).toBeNull();
    });

    it("DRAFT: editing one field and saving preserves DE/NDE as independent values, never collapsed", async () => {
      const onSaveDraft = vi.fn().mockResolvedValue();
      render(
        <ConditionMonitoringReadingDetailPanel
          reading={baseReading({ bearingTempDe: 61, bearingTempNde: 58 })}
          canWrite
          onSaveDraft={onSaveDraft}
        />
      );

      fireEvent.change(await screen.findByLabelText("Bearing Temp DE"), { target: { value: "65" } });
      fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      await waitFor(() => expect(onSaveDraft).toHaveBeenCalled());
      const { measurements } = onSaveDraft.mock.calls[0][1];
      expect(measurements.bearing_temp_de).toBe(65);
      expect(measurements.bearing_temp_nde).toBe(58); // untouched sibling preserved, not wiped
    });

    it("DRAFT: saving preserves an explicitly-entered zero", async () => {
      const onSaveDraft = vi.fn().mockResolvedValue();
      render(<ConditionMonitoringReadingDetailPanel reading={baseReading()} canWrite onSaveDraft={onSaveDraft} />);

      fireEvent.change(await screen.findByLabelText("Motor Current"), { target: { value: "0" } });
      fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      await waitFor(() => expect(onSaveDraft).toHaveBeenCalled());
      expect(onSaveDraft.mock.calls[0][1].measurements.motor_current).toBe(0);
    });

    // MWO-LTSA-PM-CMON-FOUNDATION-CLEANUP-001 -- flushing/quench/flushing-
    // in-out/cooling-water-in-out/water-jacket are no longer out-of-scope
    // passthrough fields; they are fully managed, editable, golden-
    // evidence-backed fields (ADR-CONDITION-MONITORING-001) like every
    // other measurement.
    it("DRAFT: an untouched legacy field (flushing temp) is preserved unmodified on save", async () => {
      const onSaveDraft = vi.fn().mockResolvedValue();
      render(
        <ConditionMonitoringReadingDetailPanel
          reading={baseReading({ flushingTempDe: 45, flushingTempNde: 44 })}
          canWrite
          onSaveDraft={onSaveDraft}
        />
      );

      fireEvent.click(await screen.findByRole("button", { name: "Save Draft" }));

      await waitFor(() => expect(onSaveDraft).toHaveBeenCalled());
      const { measurements } = onSaveDraft.mock.calls[0][1];
      expect(measurements.flushing_temp_de).toBe(45);
      expect(measurements.flushing_temp_nde).toBe(44);
    });

    it("DRAFT: every legacy golden CMON field is editable and pre-filled from the real record", async () => {
      const onSaveDraft = vi.fn().mockResolvedValue();
      render(
        <ConditionMonitoringReadingDetailPanel
          reading={baseReading({ waterJacketTempDe: 60, waterJacketTempNde: null })}
          canWrite
          onSaveDraft={onSaveDraft}
        />
      );

      expect(await screen.findByLabelText("Water Jacket Temp DE")).toHaveProperty("value", "60");
      expect(screen.getByLabelText("Water Jacket Temp NDE")).toHaveProperty("value", "");

      fireEvent.change(screen.getByLabelText("Cooling Water In Temp DE"), { target: { value: "25" } });
      fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      await waitFor(() => expect(onSaveDraft).toHaveBeenCalled());
      const { measurements } = onSaveDraft.mock.calls[0][1];
      expect(measurements.cooling_water_in_temp_de).toBe(25);
      expect(measurements.water_jacket_temp_de).toBe(60);
      expect(measurements.water_jacket_temp_nde).toBeNull(); // honestly null, not fabricated
    });

    it("leak tri-state: not recorded stays null, never inferred as No Leak", async () => {
      const onSaveDraft = vi.fn().mockResolvedValue();
      render(
        <ConditionMonitoringReadingDetailPanel
          reading={baseReading({ leakDe: null, leakNde: null })}
          canWrite
          onSaveDraft={onSaveDraft}
        />
      );

      expect(await screen.findByLabelText("Leak Status DE")).toHaveProperty("value", "");
      fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      await waitFor(() => expect(onSaveDraft).toHaveBeenCalled());
      const { measurements } = onSaveDraft.mock.calls[0][1];
      expect(measurements.mechanical_seal_leak_de).toBeNull();
      expect(measurements.mechanical_seal_leak_nde).toBeNull();
    });

    it("leak tri-state: DE and NDE are captured independently", async () => {
      const onSaveDraft = vi.fn().mockResolvedValue();
      render(<ConditionMonitoringReadingDetailPanel reading={baseReading()} canWrite onSaveDraft={onSaveDraft} />);

      fireEvent.change(await screen.findByLabelText("Leak Status DE"), { target: { value: "true" } });
      fireEvent.change(screen.getByLabelText("Leak Status NDE"), { target: { value: "false" } });
      fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      await waitFor(() => expect(onSaveDraft).toHaveBeenCalled());
      const { measurements } = onSaveDraft.mock.calls[0][1];
      expect(measurements.mechanical_seal_leak_de).toBe(true);
      expect(measurements.mechanical_seal_leak_nde).toBe(false);
    });

    it("RETURNED_FOR_CORRECTION: measurement fields remain editable, pre-filled from the real record", async () => {
      render(
        <ConditionMonitoringReadingDetailPanel
          reading={baseReading({ workflowStatus: "RETURNED_FOR_CORRECTION", motorCurrent: 22.1 })}
          canWrite
        />
      );

      expect(await screen.findByLabelText("Motor Current")).toHaveProperty("value", "22.1");
    });

    it("SUBMITTED/FINALIZED: measurement fields are read-only, not editable inputs", async () => {
      render(<ConditionMonitoringReadingDetailPanel reading={baseReading({ workflowStatus: "SUBMITTED" })} canWrite />);

      await screen.findByText("Reading Summary");
      expect(screen.queryByLabelText("Motor Current")).toBeNull();
      expect(screen.queryByLabelText("Bearing Temp DE")).toBeNull();
      expect(screen.queryByLabelText("Leak Status DE")).toBeNull();
    });

    it("JC never sees measurement edit inputs (no impersonation of TAP-recorded values)", async () => {
      render(
        <ConditionMonitoringReadingDetailPanel
          reading={baseReading({ workflowStatus: "SUBMITTED", bearingTempDe: 61 })}
          canTechnicalReview
        />
      );

      await screen.findByText("John Crane Technical Review");
      expect(screen.queryByLabelText("Bearing Temp DE")).toBeNull();
      // The real TAP-recorded value is still visible, just not editable.
      expect(screen.getByText("61 °C / —")).toBeTruthy();
    });
  });
});
