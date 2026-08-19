import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import HistoricalReview from "./HistoricalReview";
import {
  getHistoricalReviewCandidates,
  reviewHistoricalReviewCandidate,
  rejectHistoricalReviewCandidate,
  promoteHistoricalReviewCandidate,
} from "../../../api/ai5rClient";
import { AuthProvider } from "../auth/AuthContext";

// MWO-LTSA-HISTORICAL-REVIEW-UI-001
vi.mock("../../../api/ai5rClient", () => ({
  getHistoricalReviewCandidates: vi.fn(),
  getHistoricalReviewCandidate: vi.fn(),
  reviewHistoricalReviewCandidate: vi.fn(),
  rejectHistoricalReviewCandidate: vi.fn(),
  promoteHistoricalReviewCandidate: vi.fn(),
  onUnauthorized: vi.fn(),
}));

function renderWithSession(permissions, role = "SUPERUSER") {
  const client = {
    getSession: () =>
      Promise.resolve({
        user: { name: "Test User" },
        organization: { displayName: "TAP" },
        role,
        permissions,
      }),
  };
  return render(
    <AuthProvider client={client}>
      <HistoricalReview />
    </AuthProvider>
  );
}

const MATCHED_CANDIDATE = {
  document_field_extraction_id: "DFE-1",
  source_document_id: "PDF-HOC-JULY-2026",
  source_document_type: "PDF",
  detected_document_type: "HISTORICAL_CMON_READING_CANDIDATE",
  extraction_provider: "deterministic_workbook_table_parser",
  extracted_fields: { mechseal_temp_de: 58.0, quench_temp_de: null, asset_type: "PUMP" },
  reviewed_fields: null,
  status: "PENDING_REVIEW",
  pump_tag_number: "110-P-9A",
  source_page: null,
};

const UNRESOLVED_CANDIDATE = {
  ...MATCHED_CANDIDATE,
  document_field_extraction_id: "DFE-2",
  pump_tag_number: null,
};

afterEach(() => {
  vi.clearAllMocks();
});

describe("Historical Data Review workspace -- access", () => {
  it("shows an access-restricted message for a role without record.edit", async () => {
    renderWithSession(["maintenance.read"], "TAP_ENGINEER");
    expect(await screen.findByText("Access restricted")).toBeInTheDocument();
    expect(getHistoricalReviewCandidates).not.toHaveBeenCalled();
  });

  it("loads candidates for a SUPERUSER session", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([MATCHED_CANDIDATE]);
    renderWithSession(["record.edit"], "SUPERUSER");
    await waitFor(() => expect(getHistoricalReviewCandidates).toHaveBeenCalled());
    expect(await screen.findByText("DFE-1")).toBeInTheDocument();
  });

  it("loads candidates for a TAP_ADMIN session", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([MATCHED_CANDIDATE]);
    renderWithSession(["record.edit"], "TAP_ADMIN");
    await waitFor(() => expect(getHistoricalReviewCandidates).toHaveBeenCalled());
    expect(await screen.findByText("DFE-1")).toBeInTheDocument();
  });
});

describe("Historical Data Review workspace -- summary and filters", () => {
  it("summarizes matched vs needs-resolution counts", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([MATCHED_CANDIDATE, UNRESOLVED_CANDIDATE]);
    renderWithSession(["record.edit"]);
    const summary = await screen.findByTestId("historical-review-summary");
    expect(summary).toHaveTextContent("2"); // total pending
    expect(summary).toHaveTextContent("1"); // matched / needs resolution
  });
});

describe("Historical Data Review workspace -- detail and N/A display", () => {
  it("shows N/A for a NULL extracted field, never fabricating a value", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([MATCHED_CANDIDATE]);
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("DFE-1"));
    const sourceCell = await screen.findByTestId("source-value-quench_temp_de");
    expect(sourceCell).toHaveTextContent("N/A");
  });

  it("shows a real 0 value distinctly from N/A", async () => {
    const candidate = {
      ...MATCHED_CANDIDATE,
      extracted_fields: { ...MATCHED_CANDIDATE.extracted_fields, mechseal_temp_de: 0 },
    };
    getHistoricalReviewCandidates.mockResolvedValue([candidate]);
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("DFE-1"));
    const sourceCell = await screen.findByTestId("source-value-mechseal_temp_de");
    expect(sourceCell).toHaveTextContent("0");
    expect(sourceCell).not.toHaveTextContent("N/A");
  });
});

describe("Historical Data Review workspace -- MWO-LTSA-HISTORICAL-INCOMPLETE-DATA-POLICY-001 Core Model", () => {
  it("shows Incomplete (never a fabricated Matched) for a candidate with no resolved pump tag", async () => {
    const incomplete = {
      ...UNRESOLVED_CANDIDATE,
      classification: "INCOMPLETE",
      extracted_fields: { ...UNRESOLVED_CANDIDATE.extracted_fields, raw_asset_tag: "701-MM-51" },
    };
    getHistoricalReviewCandidates.mockResolvedValue([incomplete]);
    renderWithSession(["record.edit"]);
    const badges = await screen.findAllByText("Incomplete");
    expect(badges.length).toBeGreaterThan(0);
  });

  it("displays the raw source tag distinctly from the (unresolved) canonical pump relation", async () => {
    const incomplete = {
      ...UNRESOLVED_CANDIDATE,
      classification: "INCOMPLETE",
      extracted_fields: { ...UNRESOLVED_CANDIDATE.extracted_fields, raw_asset_tag: "701-MM-51" },
    };
    getHistoricalReviewCandidates.mockResolvedValue([incomplete]);
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("DFE-2"));
    const modal = await screen.findByTestId("modal");
    expect(within(modal).getAllByText(/701-MM-51/).length).toBeGreaterThan(0);
    // canonical pump relation is genuinely unresolved -- N/A, never a
    // guessed/converted pump tag (e.g. never "701-P-51").
    expect(within(modal).queryByText("701-P-51")).not.toBeInTheDocument();
  });
});

describe("Historical Data Review workspace -- actions", () => {
  it("confirm does not require a reason", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([MATCHED_CANDIDATE]);
    reviewHistoricalReviewCandidate.mockResolvedValue({ ...MATCHED_CANDIDATE, status: "REVIEWED" });
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("DFE-1"));
    fireEvent.click(await screen.findByText("Confirm As Extracted"));
    await waitFor(() => expect(reviewHistoricalReviewCandidate).toHaveBeenCalledWith("DFE-1", {}));
  });

  it("resolving a pump match calls the review endpoint with the tag and reason", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([UNRESOLVED_CANDIDATE]);
    reviewHistoricalReviewCandidate.mockResolvedValue({ ...UNRESOLVED_CANDIDATE, pump_tag_number: "110-P-9A" });
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("DFE-2"));
    fireEvent.change(await screen.findByLabelText("pump-tag-input"), { target: { value: "110-P-9A" } });
    fireEvent.change(screen.getByLabelText("reason"), { target: { value: "Whitespace variant confirmed" } });
    fireEvent.click(screen.getByRole("button", { name: "Resolve Pump Match" }));
    await waitFor(() =>
      expect(reviewHistoricalReviewCandidate).toHaveBeenCalledWith("DFE-2", {
        pumpTagNumber: "110-P-9A",
        reason: "Whitespace variant confirmed",
      })
    );
  });

  it("promote is disabled until the candidate is REVIEWED with a resolved pump", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([UNRESOLVED_CANDIDATE]);
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("DFE-2"));
    expect(await screen.findByRole("button", { name: "Promote" })).toBeDisabled();
  });

  it("promote becomes available right after a Confirm makes the candidate REVIEWED, without a page reload", async () => {
    // Mirrors the real flow: list_pending() only ever returns
    // PENDING_REVIEW candidates (the real repository's own capability),
    // so a REVIEWED candidate can only become visible in-session via an
    // actual review action -- never by starting REVIEWED on initial load.
    getHistoricalReviewCandidates.mockResolvedValue([MATCHED_CANDIDATE]);
    const reviewed = { ...MATCHED_CANDIDATE, status: "REVIEWED" };
    reviewHistoricalReviewCandidate.mockResolvedValue(reviewed);
    promoteHistoricalReviewCandidate.mockResolvedValue({ pm_occurrence_code: "PMOCC-NEW" });
    renderWithSession(["record.edit"]);

    fireEvent.click(await screen.findByText("DFE-1"));
    expect(await screen.findByRole("button", { name: "Promote" })).toBeDisabled();

    fireEvent.click(screen.getByText("Confirm As Extracted"));
    await waitFor(() => expect(reviewHistoricalReviewCandidate).toHaveBeenCalled());

    const promoteButton = await screen.findByRole("button", { name: "Promote" });
    expect(promoteButton).not.toBeDisabled();
    fireEvent.click(promoteButton);
    await waitFor(() => expect(promoteHistoricalReviewCandidate).toHaveBeenCalledWith("DFE-1"));
  });

  it("reject calls the reject endpoint with the reason", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([MATCHED_CANDIDATE]);
    rejectHistoricalReviewCandidate.mockResolvedValue({ ...MATCHED_CANDIDATE, status: "REJECTED" });
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("DFE-1"));
    fireEvent.change(await screen.findByLabelText("reason"), { target: { value: "Duplicate of a live reading" } });
    fireEvent.click(screen.getByText("Reject"));
    await waitFor(() =>
      expect(rejectHistoricalReviewCandidate).toHaveBeenCalledWith("DFE-1", "Duplicate of a live reading")
    );
  });
});
