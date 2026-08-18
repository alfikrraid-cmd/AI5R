import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import EvidenceAttachments, { EVIDENCE_RECORD_TYPES } from "./EvidenceAttachments";
import { getPMCMEvidence, pmCMEvidenceDownloadUrl, uploadPMCMEvidence } from "../../../api/ai5rClient";

// MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 2 -- the ONE canonical evidence
// widget, tested in isolation (not only via PM.jsx/ConditionMonitoring.jsx
// page tests) so its upload/list/error states are directly proven.
vi.mock("../../../api/ai5rClient", () => ({
  getPMCMEvidence: vi.fn(),
  uploadPMCMEvidence: vi.fn(),
  pmCMEvidenceDownloadUrl: vi.fn((id) => `https://example.test/evidence/${id}/download`),
}));

afterEach(() => {
  vi.clearAllMocks();
});

const EXISTING_EVIDENCE = [
  {
    evidence_id: "EVID-1",
    file_name: "mechseal-photo.jpg",
    content_type: "image/jpeg",
    file_size_bytes: 204800,
    category: "PHOTO",
    source: "MANUAL",
    uploaded_by: "user-uuid-123",
    uploaded_at: "2026-08-01T10:00:00Z",
  },
];

describe("EvidenceAttachments (shared PM/CMON evidence widget)", () => {
  it("renders a loading state before the evidence list resolves", () => {
    getPMCMEvidence.mockReturnValue(new Promise(() => {}));
    render(<EvidenceAttachments recordType={EVIDENCE_RECORD_TYPES.PM_OCCURRENCE} recordCode="PMOCC-1" canUpload={false} />);

    expect(screen.getByText("Loading evidence...")).toBeTruthy();
  });

  it("renders 'No evidence attached.' honestly, never fabricated data, when the list is empty", async () => {
    getPMCMEvidence.mockResolvedValue([]);
    render(<EvidenceAttachments recordType={EVIDENCE_RECORD_TYPES.PM_OCCURRENCE} recordCode="PMOCC-1" canUpload={false} />);

    expect(await screen.findByText("No evidence attached.")).toBeTruthy();
  });

  it("renders every real evidence record's filename/category/timestamp/uploader/source (reload persistence)", async () => {
    getPMCMEvidence.mockResolvedValue(EXISTING_EVIDENCE);
    render(<EvidenceAttachments recordType={EVIDENCE_RECORD_TYPES.PM_OCCURRENCE} recordCode="PMOCC-1" canUpload={false} />);

    expect(await screen.findByText("mechseal-photo.jpg")).toBeTruthy();
    expect(screen.getByText("PHOTO")).toBeTruthy();
    expect(screen.getByText(/image\/jpeg/)).toBeTruthy();
    expect(screen.getByText(/Uploaded by user-uuid-123/)).toBeTruthy();
    expect(screen.getByText(/2026-08-01T10:00:00Z/)).toBeTruthy();
    expect(getPMCMEvidence).toHaveBeenCalledWith(EVIDENCE_RECORD_TYPES.PM_OCCURRENCE, "PMOCC-1");
  });

  it("shows 'Unable to load evidence.' with a Retry action on a load failure, never fabricated data", async () => {
    getPMCMEvidence.mockRejectedValueOnce(new Error("network down"));
    render(<EvidenceAttachments recordType={EVIDENCE_RECORD_TYPES.PM_OCCURRENCE} recordCode="PMOCC-1" canUpload={false} />);

    expect(await screen.findByText("Unable to load evidence.")).toBeTruthy();

    getPMCMEvidence.mockResolvedValueOnce(EXISTING_EVIDENCE);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("mechseal-photo.jpg")).toBeTruthy();
  });

  it("hides the upload controls entirely when canUpload is false (e.g. Pertamina / non-editable states)", async () => {
    getPMCMEvidence.mockResolvedValue([]);
    render(<EvidenceAttachments recordType={EVIDENCE_RECORD_TYPES.PM_OCCURRENCE} recordCode="PMOCC-1" canUpload={false} />);

    await screen.findByText("No evidence attached.");
    expect(screen.queryByTestId("evidence-file-input")).toBeNull();
    expect(screen.queryByText(/Upload Photo/)).toBeNull();
  });

  it("uploads a file via the real evidence API and appends the server response, never a fabricated row", async () => {
    getPMCMEvidence.mockResolvedValue([]);
    uploadPMCMEvidence.mockResolvedValue({
      data: {
        evidence_id: "EVID-NEW",
        file_name: "reading.pdf",
        content_type: "application/pdf",
        file_size_bytes: 51200,
        category: "PHOTO",
        source: "MANUAL",
        uploaded_by: "user-uuid-999",
        uploaded_at: "2026-08-16T08:00:00Z",
      },
    });
    render(<EvidenceAttachments recordType={EVIDENCE_RECORD_TYPES.CONDITION_MONITORING_READING} recordCode="CMONR-1" canUpload />);
    await screen.findByText("No evidence attached.");

    const file = new File(["dummy"], "reading.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByTestId("evidence-file-input"), { target: { files: [file] } });

    expect(await screen.findByTestId("evidence-upload-success")).toHaveProperty("textContent", "reading.pdf uploaded.");
    expect(await screen.findByText("reading.pdf")).toBeTruthy();
    expect(uploadPMCMEvidence).toHaveBeenCalledWith(
      expect.objectContaining({
        recordType: EVIDENCE_RECORD_TYPES.CONDITION_MONITORING_READING,
        recordCode: "CMONR-1",
        category: "PHOTO",
        file,
      })
    );
  });

  it("surfaces a verbatim upload error and never fakes a successful upload", async () => {
    getPMCMEvidence.mockResolvedValue([]);
    uploadPMCMEvidence.mockRejectedValueOnce(new Error("unsupported content type 'image/gif'"));
    render(<EvidenceAttachments recordType={EVIDENCE_RECORD_TYPES.PM_OCCURRENCE} recordCode="PMOCC-1" canUpload />);
    await screen.findByText("No evidence attached.");

    const file = new File(["dummy"], "bad.gif", { type: "image/gif" });
    fireEvent.change(screen.getByTestId("evidence-file-input"), { target: { files: [file] } });

    expect(await screen.findByTestId("evidence-upload-error")).toHaveProperty(
      "textContent",
      "unsupported content type 'image/gif'"
    );
    expect(screen.getByText("No evidence attached.")).toBeTruthy();
    expect(screen.queryByTestId("evidence-upload-success")).toBeNull();
  });

  it("does not fetch or render anything when no recordCode exists yet", () => {
    render(<EvidenceAttachments recordType={EVIDENCE_RECORD_TYPES.PM_OCCURRENCE} recordCode={null} canUpload={false} />);

    expect(getPMCMEvidence).not.toHaveBeenCalled();
  });

  it("builds a download URL via the real pmCMEvidenceDownloadUrl helper, not a fabricated link", async () => {
    getPMCMEvidence.mockResolvedValue(EXISTING_EVIDENCE);
    render(<EvidenceAttachments recordType={EVIDENCE_RECORD_TYPES.PM_OCCURRENCE} recordCode="PMOCC-1" canUpload={false} />);

    const link = await screen.findByText("mechseal-photo.jpg");
    expect(link.closest("a")).toHaveProperty("href", "https://example.test/evidence/EVID-1/download");
    expect(pmCMEvidenceDownloadUrl).toHaveBeenCalledWith("EVID-1");
  });
});
