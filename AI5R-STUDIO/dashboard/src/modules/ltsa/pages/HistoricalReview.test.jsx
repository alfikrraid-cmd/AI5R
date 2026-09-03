import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import HistoricalReview from "./HistoricalReview";
import {
  getHistoricalReviewCandidates,
  reviewHistoricalReviewCandidate,
  rejectHistoricalReviewCandidate,
  promoteHistoricalReviewCandidate,
  bulkReviewHistoricalReviewCandidates,
} from "../../../api/ai5rClient";
import { AuthProvider } from "../auth/AuthContext";

// MWO-LTSA-HISTORICAL-REVIEW-UI-001 / MWO-LTSA-BULK-HISTORICAL-REVIEW-001
vi.mock("../../../api/ai5rClient", () => ({
  getHistoricalReviewCandidates: vi.fn(),
  getHistoricalReviewCandidate: vi.fn(),
  reviewHistoricalReviewCandidate: vi.fn(),
  rejectHistoricalReviewCandidate: vi.fn(),
  promoteHistoricalReviewCandidate: vi.fn(),
  bulkReviewHistoricalReviewCandidates: vi.fn(),
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

const PM_CANDIDATE_A = {
  ...MATCHED_CANDIDATE,
  document_field_extraction_id: "DFE-PM-1",
  detected_document_type: "HISTORICAL_PM_OCCURRENCE_CANDIDATE",
};

const PM_CANDIDATE_B = {
  ...MATCHED_CANDIDATE,
  document_field_extraction_id: "DFE-PM-2",
  detected_document_type: "HISTORICAL_PM_OCCURRENCE_CANDIDATE",
};

// MWO-LTSA-EXACT-540-RECOVERY-UI-001 -- recovery_batch_eligible is a
// SERVER-derived field (routers/historical_review.py::_is_recovery_
// batch_eligible); these fixtures set it exactly as the real backend
// would, so the tests below prove the frontend trusts that flag rather
// than re-deriving eligibility itself.
const RECOVERY_CANDIDATE_A = {
  ...PM_CANDIDATE_A,
  document_field_extraction_id: "DFE-REC-1",
  extracted_fields: { ...PM_CANDIDATE_A.extracted_fields, candidate_identity_v2: "HASH-1" },
  recovery_batch_eligible: true,
};

const RECOVERY_CANDIDATE_B = {
  ...PM_CANDIDATE_B,
  document_field_extraction_id: "DFE-REC-2",
  extracted_fields: { ...PM_CANDIDATE_B.extracted_fields, candidate_identity_v2: "HASH-2" },
  recovery_batch_eligible: true,
};

const OLD_PENDING_PM_CANDIDATE = {
  ...PM_CANDIDATE_A,
  document_field_extraction_id: "DFE-OLD-PM",
  recovery_batch_eligible: false, // no candidate_identity_v2, server says not eligible
};

const CMON_PENDING_CANDIDATE = {
  ...MATCHED_CANDIDATE,
  document_field_extraction_id: "DFE-CMON-1",
  recovery_batch_eligible: false,
};

const FINDING_PENDING_CANDIDATE = {
  ...MATCHED_CANDIDATE,
  document_field_extraction_id: "DFE-FIND-1",
  detected_document_type: "HISTORICAL_FINDING_CANDIDATE",
  recovery_batch_eligible: false,
};

// A candidate that HAS candidate_identity_v2 in its raw fields but the
// server still flagged it ineligible (e.g. wrong status/domain) -- the
// frontend must trust the flag, never re-derive from field presence.
const MALFORMED_V2_CANDIDATE = {
  ...PM_CANDIDATE_A,
  document_field_extraction_id: "DFE-MALFORMED",
  extracted_fields: { ...PM_CANDIDATE_A.extracted_fields, candidate_identity_v2: "HASH-SUSPECT" },
  recovery_batch_eligible: false,
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
    // findByTestId resolves as soon as the element exists, which can be
    // before the async candidate load lands -- wait for the real content,
    // not just the element's presence.
    await waitFor(() => expect(summary).toHaveTextContent("2")); // total pending
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

describe("Historical Data Review workspace -- bulk review", () => {
  it("only offers PM candidates as bulk-selectable, never CMON", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([MATCHED_CANDIDATE, PM_CANDIDATE_A]);
    renderWithSession(["record.edit"]);
    const panel = await screen.findByTestId("bulk-review-panel");
    expect(within(panel).getByLabelText("select-DFE-PM-1")).toBeInTheDocument();
    expect(within(panel).queryByLabelText("select-DFE-1")).not.toBeInTheDocument();
  });

  it("select all filtered selects exactly the eligible PM candidates and shows the count", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([PM_CANDIDATE_A, PM_CANDIDATE_B, MATCHED_CANDIDATE]);
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("Select All Filtered PM (2)"));
    expect(await screen.findByTestId("bulk-review-summary")).toHaveTextContent("2 selected of 2 eligible");
  });

  it("requires explicit confirmation before calling the bulk endpoint", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([PM_CANDIDATE_A, PM_CANDIDATE_B]);
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByLabelText("select-DFE-PM-1"));
    fireEvent.click(await screen.findByLabelText("select-DFE-PM-2"));
    fireEvent.click(screen.getByText("Bulk Review Selected (2)"));

    const modal = await screen.findByTestId("modal");
    expect(modal).toHaveTextContent("confirm-as-extracted");
    expect(within(modal).getByText("2")).toBeInTheDocument(); // the <strong> count
    expect(bulkReviewHistoricalReviewCandidates).not.toHaveBeenCalled();

    fireEvent.click(within(modal).getByText("Confirm Bulk Review of 2"));
    await waitFor(() =>
      expect(bulkReviewHistoricalReviewCandidates).toHaveBeenCalledWith(["DFE-PM-1", "DFE-PM-2"])
    );
  });

  it("cancelling the confirm dialog never calls the bulk endpoint", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([PM_CANDIDATE_A]);
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByLabelText("select-DFE-PM-1"));
    fireEvent.click(screen.getByText("Bulk Review Selected (1)"));
    const modal = await screen.findByTestId("modal");
    fireEvent.click(within(modal).getByText("Cancel"));
    expect(screen.queryByTestId("modal")).not.toBeInTheDocument();
    expect(bulkReviewHistoricalReviewCandidates).not.toHaveBeenCalled();
  });

  it("shows the reviewed count on success and reloads the list", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([PM_CANDIDATE_A]);
    bulkReviewHistoricalReviewCandidates.mockResolvedValue({
      reviewed_count: 1,
      candidate_ids: ["DFE-PM-1"],
    });
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByLabelText("select-DFE-PM-1"));
    fireEvent.click(screen.getByText("Bulk Review Selected (1)"));
    fireEvent.click(await screen.findByText("Confirm Bulk Review of 1"));
    await waitFor(() => expect(screen.getByText("Bulk reviewed 1 candidate(s).")).toBeInTheDocument());
    // called once for initial load, once more after the bulk action reloads
    await waitFor(() => expect(getHistoricalReviewCandidates).toHaveBeenCalledTimes(2));
  });

  it("bulk review never calls promote -- promotion stays a separate action", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([PM_CANDIDATE_A]);
    bulkReviewHistoricalReviewCandidates.mockResolvedValue({ reviewed_count: 1, candidate_ids: ["DFE-PM-1"] });
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByLabelText("select-DFE-PM-1"));
    fireEvent.click(screen.getByText("Bulk Review Selected (1)"));
    fireEvent.click(await screen.findByText("Confirm Bulk Review of 1"));
    await waitFor(() => expect(bulkReviewHistoricalReviewCandidates).toHaveBeenCalled());
    expect(promoteHistoricalReviewCandidate).not.toHaveBeenCalled();
  });

  it("clear selection empties the selected count", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([PM_CANDIDATE_A, PM_CANDIDATE_B]);
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("Select All Filtered PM (2)"));
    await screen.findByText("Bulk Review Selected (2)");
    fireEvent.click(screen.getByText("Clear Selection"));
    expect(await screen.findByTestId("bulk-review-summary")).toHaveTextContent("0 selected of 2 eligible");
  });
});

describe("Historical Data Review workspace -- Historical PM Recovery (MWO-LTSA-EXACT-540-RECOVERY-UI-001)", () => {
  it("counts only server-flagged recovery-eligible candidates as verified", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([
      RECOVERY_CANDIDATE_A, RECOVERY_CANDIDATE_B, OLD_PENDING_PM_CANDIDATE,
      CMON_PENDING_CANDIDATE, FINDING_PENDING_CANDIDATE,
    ]);
    renderWithSession(["record.edit"]);
    const summary = await screen.findByTestId("recovery-summary");
    expect(summary).toHaveTextContent("Verified candidates:");
    expect(within(summary).getByText("2")).toBeInTheDocument(); // 2 recovery-eligible
    expect(within(summary).getByText("3")).toBeInTheDocument(); // 3 excluded (old PM + CMON + Finding)
  });

  it("excludes the old pending PM candidate from the recovery request", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([RECOVERY_CANDIDATE_A, OLD_PENDING_PM_CANDIDATE]);
    bulkReviewHistoricalReviewCandidates.mockResolvedValue({ reviewed_count: 1, candidate_ids: ["DFE-REC-1"] });
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("Review 1 Verified PM"));
    fireEvent.click(await screen.findByText("Confirm Review of 1"));
    await waitFor(() => expect(bulkReviewHistoricalReviewCandidates).toHaveBeenCalledWith(["DFE-REC-1"]));
  });

  it("excludes CMON candidates from the recovery request", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([RECOVERY_CANDIDATE_A, CMON_PENDING_CANDIDATE]);
    bulkReviewHistoricalReviewCandidates.mockResolvedValue({ reviewed_count: 1, candidate_ids: ["DFE-REC-1"] });
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("Review 1 Verified PM"));
    fireEvent.click(await screen.findByText("Confirm Review of 1"));
    await waitFor(() =>
      expect(bulkReviewHistoricalReviewCandidates).toHaveBeenCalledWith(
        expect.not.arrayContaining(["DFE-CMON-1"])
      )
    );
  });

  it("excludes Finding candidates from the recovery request", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([RECOVERY_CANDIDATE_A, FINDING_PENDING_CANDIDATE]);
    bulkReviewHistoricalReviewCandidates.mockResolvedValue({ reviewed_count: 1, candidate_ids: ["DFE-REC-1"] });
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("Review 1 Verified PM"));
    fireEvent.click(await screen.findByText("Confirm Review of 1"));
    await waitFor(() =>
      expect(bulkReviewHistoricalReviewCandidates).toHaveBeenCalledWith(
        expect.not.arrayContaining(["DFE-FIND-1"])
      )
    );
  });

  it("the generic bulk panel's larger PM count never leaks into the recovery request", async () => {
    // The generic panel would offer BOTH PM candidates (2) via "Select
    // All Filtered PM" since it filters by type only -- the dedicated
    // recovery action must still submit only the 1 flagged as eligible.
    getHistoricalReviewCandidates.mockResolvedValue([RECOVERY_CANDIDATE_A, OLD_PENDING_PM_CANDIDATE]);
    bulkReviewHistoricalReviewCandidates.mockResolvedValue({ reviewed_count: 1, candidate_ids: ["DFE-REC-1"] });
    renderWithSession(["record.edit"]);
    expect(await screen.findByText("Select All Filtered PM (2)")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Review 1 Verified PM"));
    fireEvent.click(await screen.findByText("Confirm Review of 1"));
    await waitFor(() => expect(bulkReviewHistoricalReviewCandidates).toHaveBeenCalledWith(["DFE-REC-1"]));
  });

  it("a candidate missing candidate_identity_v2 (server flag false) is excluded", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([RECOVERY_CANDIDATE_A, OLD_PENDING_PM_CANDIDATE]);
    renderWithSession(["record.edit"]);
    const summary = await screen.findByTestId("recovery-summary");
    // only RECOVERY_CANDIDATE_A is verified; OLD_PENDING_PM_CANDIDATE (no
    // candidate_identity_v2) is the one excluded -- both counts happen
    // to read "1" here, so assert the full sentence instead of a bare digit.
    await waitFor(() => expect(summary).toHaveTextContent("Verified candidates: 1"));
    expect(summary).toHaveTextContent("Excluded pending candidates: 1");
  });

  it("trusts the server's recovery_batch_eligible flag over raw field presence (malformed/non-target case)", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([RECOVERY_CANDIDATE_A, MALFORMED_V2_CANDIDATE]);
    bulkReviewHistoricalReviewCandidates.mockResolvedValue({ reviewed_count: 1, candidate_ids: ["DFE-REC-1"] });
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("Review 1 Verified PM"));
    fireEvent.click(await screen.findByText("Confirm Review of 1"));
    await waitFor(() => expect(bulkReviewHistoricalReviewCandidates).toHaveBeenCalledWith(["DFE-REC-1"]));
  });

  it("sends the exact unique id list of every recovery-eligible candidate", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([RECOVERY_CANDIDATE_A, RECOVERY_CANDIDATE_B]);
    bulkReviewHistoricalReviewCandidates.mockResolvedValue({ reviewed_count: 2, candidate_ids: ["DFE-REC-1", "DFE-REC-2"] });
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("Review 2 Verified PM"));
    fireEvent.click(await screen.findByText("Confirm Review of 2"));
    await waitFor(() =>
      expect(bulkReviewHistoricalReviewCandidates).toHaveBeenCalledWith(["DFE-REC-1", "DFE-REC-2"])
    );
  });

  it("the confirmation dialog displays the exact verified count before submission", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([RECOVERY_CANDIDATE_A, RECOVERY_CANDIDATE_B, OLD_PENDING_PM_CANDIDATE]);
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("Review 2 Verified PM"));
    const modal = await screen.findByTestId("modal");
    expect(modal).toHaveTextContent("Review exactly");
    expect(within(modal).getByText("2")).toBeInTheDocument();
    expect(bulkReviewHistoricalReviewCandidates).not.toHaveBeenCalled();
  });

  it("a backend rejection shows an error, never an optimistic success message", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([RECOVERY_CANDIDATE_A]);
    bulkReviewHistoricalReviewCandidates.mockRejectedValue(new Error("one or more candidates are not eligible"));
    renderWithSession(["record.edit"]);
    fireEvent.click(await screen.findByText("Review 1 Verified PM"));
    fireEvent.click(await screen.findByText("Confirm Review of 1"));
    await waitFor(() => expect(screen.getByText("one or more candidates are not eligible")).toBeInTheDocument());
    expect(screen.queryByText(/reviewed 1 candidate/)).not.toBeInTheDocument();
  });

  it("action is disabled (fail-closed) when there is nothing recovery-eligible", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([OLD_PENDING_PM_CANDIDATE, CMON_PENDING_CANDIDATE]);
    renderWithSession(["record.edit"]);
    expect(await screen.findByText("Review 0 Verified PM")).toBeDisabled();
  });

  it("existing generic Bulk Review panel is untouched by the recovery panel's presence", async () => {
    getHistoricalReviewCandidates.mockResolvedValue([RECOVERY_CANDIDATE_A, PM_CANDIDATE_B]);
    renderWithSession(["record.edit"]);
    // generic panel still offers both PM candidates independently of
    // the recovery flag.
    expect(await screen.findByText("Select All Filtered PM (2)")).toBeInTheDocument();
    expect(await screen.findByText("Review 1 Verified PM")).toBeInTheDocument();
  });
});
