import { useEffect, useMemo, useState } from "react";
import { Badge, Button, EmptyState, MetricCard, Modal, PageHeader, Table } from "../../../design-system";
import {
  getHistoricalReviewCandidates,
  reviewHistoricalReviewCandidate,
  rejectHistoricalReviewCandidate,
  promoteHistoricalReviewCandidate,
  bulkReviewHistoricalReviewCandidates,
  getHistoricalPmRecoveryStatus,
  promoteHistoricalPmRecoveryBatch,
} from "../../../api/ai5rClient";
import { useOptionalAuth } from "../auth/AuthContext";
import { can, PERMISSIONS } from "../auth/permissions";
import "./HistoricalReview.css";

// MWO-LTSA-HISTORICAL-REVIEW-UI-001 -- the review/resolve/reject/promote
// workspace over the existing July staging pipeline (13a970d/5a5e186).
// record.edit-gated on the backend (SUPERUSER + TAP_ADMIN only); every
// action below simply surfaces whatever the backend already returned
// (403/404/409/422) -- no frontend-only enforcement decides access.

const TYPE_LABEL = {
  HISTORICAL_PM_OCCURRENCE_CANDIDATE: "PM",
  HISTORICAL_CMON_READING_CANDIDATE: "CMON",
  HISTORICAL_FINDING_CANDIDATE: "Finding",
};

const PROMOTABLE_TYPES = new Set(["HISTORICAL_PM_OCCURRENCE_CANDIDATE", "HISTORICAL_CMON_READING_CANDIDATE"]);

// MWO-LTSA-BULK-HISTORICAL-REVIEW-001 -- matches the backend's own
// PM-only, PENDING_REVIEW-only restriction (historical_bulk_review_
// service.py) exactly; a candidate outside this never appears as
// selectable here, so the UI never offers a selection the backend would
// reject. MAX_BULK_REVIEW_BATCH mirrors the backend's own bound (a
// client-side hint only -- the backend enforces the real limit).
const BULK_ELIGIBLE_TYPE = "HISTORICAL_PM_OCCURRENCE_CANDIDATE";
const MAX_BULK_REVIEW_BATCH = 1000;

// MWO-LTSA-HISTORICAL-INCOMPLETE-DATA-POLICY-001 -- Core Model:
// MATCHED (canonical pump relation known), INCOMPLETE (a valid
// historical observation whose pump relation is not yet resolved --
// never conflated with INVALID, never forced to resolve before
// preservation), INVALID (rejected -- never promotable). The backend
// (routers/historical_review.py::classify_candidate, the single source
// of truth) already computes and returns this on every response; this
// falls back to the same rule locally only if a response somehow lacks
// it (never re-implements a second, possibly-drifting classification).
function classificationOf(candidate) {
  if (candidate.classification) return candidate.classification;
  if (candidate.status === "REJECTED") return "INVALID";
  return candidate.pump_tag_number ? "MATCHED" : "INCOMPLETE";
}

function classificationBadge(classification) {
  if (classification === "MATCHED") return <Badge variant="success">Matched</Badge>;
  if (classification === "INVALID") return <Badge variant="danger">Invalid</Badge>;
  return <Badge variant="warning">Incomplete</Badge>;
}

// NULL/unknown display only -- the underlying value is never coerced;
// 0 is rendered as "0", never "N/A" (Hard Rule: 0 != NULL).
function displayValue(value) {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export default function HistoricalReview() {
  const authContext = useOptionalAuth();
  const canAccess = can(authContext?.session, PERMISSIONS.RECORD_EDIT);

  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [matchFilter, setMatchFilter] = useState("ALL");
  const [selectedId, setSelectedId] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);
  const [fieldEdits, setFieldEdits] = useState({});
  const [pumpTagInput, setPumpTagInput] = useState("");
  const [reasonInput, setReasonInput] = useState("");

  // MWO-LTSA-BULK-HISTORICAL-REVIEW-001 -- selection lives entirely in
  // this session's UI state; nothing is targeted server-side until the
  // human explicitly confirms and the exact id list is sent.
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [bulkConfirmOpen, setBulkConfirmOpen] = useState(false);
  const [bulkSubmitting, setBulkSubmitting] = useState(false);
  const [bulkError, setBulkError] = useState(null);
  const [bulkResult, setBulkResult] = useState(null);

  // MWO-LTSA-EXACT-540-RECOVERY-UI-001 -- a SECOND, dedicated action,
  // deliberately separate from the generic Bulk Review panel above.
  // Never a selection UI: the target set is entirely server-derived
  // (candidate.recovery_batch_eligible, computed by routers/historical_
  // review.py::_is_recovery_batch_eligible) -- this component only
  // reads that flag, it never re-implements the eligibility rule.
  const [recoveryConfirmOpen, setRecoveryConfirmOpen] = useState(false);
  const [recoverySubmitting, setRecoverySubmitting] = useState(false);
  const [recoveryError, setRecoveryError] = useState(null);
  const [recoveryResult, setRecoveryResult] = useState(null);

  // MWO-LTSA-RECOVERY-PROMOTION-001 -- terminal promotion, gated on the
  // SAME server-derived readiness the GET .../recovery/pm/status
  // endpoint computes (target/reviewed/saved/pending counts,
  // promotion_ready, current/projected final PM). This component only
  // displays that state; it never decides readiness itself.
  const [recoveryStatus, setRecoveryStatus] = useState(null);
  const [promoteConfirmOpen, setPromoteConfirmOpen] = useState(false);
  const [promoteSubmitting, setPromoteSubmitting] = useState(false);
  const [promoteError, setPromoteError] = useState(null);
  const [promoteResult, setPromoteResult] = useState(null);

  async function reload() {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await getHistoricalReviewCandidates({ status: "PENDING_REVIEW" });
      setCandidates(data);
    } catch (error) {
      setLoadError(error.message || "Failed to load historical review candidates");
    } finally {
      setLoading(false);
    }
  }

  async function loadRecoveryStatus() {
    try {
      const status = await getHistoricalPmRecoveryStatus();
      setRecoveryStatus(status);
    } catch {
      // fail-closed: no confirmed status means no Promote button, never
      // a guessed/optimistic one.
      setRecoveryStatus(null);
    }
  }

  useEffect(() => {
    if (canAccess) {
      reload();
      loadRecoveryStatus();
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canAccess]);

  // `candidates` may contain a candidate this session already reviewed
  // (kept visible in-place so its detail/Promote action stays reachable
  // -- see upsertCandidate/runAction below) even though a fresh list
  // fetch would no longer return it (list_pending() is PENDING_REVIEW
  // only, matching the real repository's own real capability). The
  // table/summary only ever count/show PENDING_REVIEW, so this never
  // misrepresents what is actually still pending.
  const pending = useMemo(() => candidates.filter((c) => c.status === "PENDING_REVIEW"), [candidates]);

  const filtered = useMemo(() => {
    return pending.filter((candidate) => {
      if (typeFilter !== "ALL" && candidate.detected_document_type !== typeFilter) return false;
      if (matchFilter !== "ALL" && classificationOf(candidate) !== matchFilter) return false;
      return true;
    });
  }, [pending, typeFilter, matchFilter]);

  // MWO-LTSA-BULK-HISTORICAL-REVIEW-001 -- "select exact recovery batch"
  // means: narrow via the existing Type/Status filters to the intended
  // batch, then select individually or via Select All Filtered. Only
  // PM PENDING_REVIEW candidates are ever offered -- matches the
  // backend's own restriction exactly, never a generic "select
  // everything" mechanism and never tied to any one batch size.
  const bulkEligible = useMemo(
    () => filtered.filter((c) => c.detected_document_type === BULK_ELIGIBLE_TYPE),
    [filtered]
  );

  // MWO-LTSA-EXACT-540-RECOVERY-UI-001 -- derived from `pending` (the
  // full still-pending set), NOT `filtered` -- this dedicated action is
  // independent of whatever the generic Type/Status dropdowns happen to
  // be set to. Every id here comes straight from the server response;
  // none are ever hard-coded in this source file.
  const recoveryEligible = useMemo(
    () => pending.filter((c) => c.recovery_batch_eligible === true),
    [pending]
  );
  const recoveryIdentities = useMemo(
    () => recoveryEligible.map((c) => (c.extracted_fields || {}).candidate_identity_v2).filter(Boolean),
    [recoveryEligible]
  );
  // Fail-closed sanity check: the server-derived set must have exactly
  // one distinct, non-empty candidate_identity_v2 per row. Any drift
  // (a duplicate identity, or a flagged row missing one) disables the
  // action entirely rather than submitting a request that might not be
  // exactly the intended batch.
  const recoveryInternallyConsistent =
    recoveryEligible.length > 0 &&
    recoveryIdentities.length === recoveryEligible.length &&
    new Set(recoveryIdentities).size === recoveryEligible.length;
  const recoveryExcludedCount = pending.length - recoveryEligible.length;

  const summary = useMemo(() => {
    // PENDING_REVIEW records are never REJECTED (a different status), so
    // INVALID never appears here -- an honest reflection of what "still
    // pending" actually means, not a fabricated third bucket.
    let matched = 0;
    let incomplete = 0;
    for (const candidate of pending) {
      if (classificationOf(candidate) === "MATCHED") matched += 1;
      else incomplete += 1;
    }
    return { total: pending.length, matched, incomplete };
  }, [pending]);

  const selected = candidates.find((c) => c.document_field_extraction_id === selectedId) || null;

  function openDetail(candidate) {
    setSelectedId(candidate.document_field_extraction_id);
    setActionError(null);
    setActionMessage(null);
    const source = candidate.reviewed_fields || candidate.extracted_fields || {};
    setFieldEdits({ ...source });
    setPumpTagInput(candidate.pump_tag_number || "");
    setReasonInput("");
  }

  function upsertCandidate(updated) {
    if (!updated) return;
    setCandidates((current) => {
      const exists = current.some((c) => c.document_field_extraction_id === updated.document_field_extraction_id);
      return exists
        ? current.map((c) => (c.document_field_extraction_id === updated.document_field_extraction_id ? updated : c))
        : [...current, updated];
    });
  }

  // A review/resolve action keeps the detail open, showing the record's
  // new status immediately (e.g. Promote becoming enabled right after a
  // REVIEWED transition) -- reject/promote are terminal for this screen,
  // so they close the detail and refresh the pending list.
  async function runAction(actionFn, { closeOnSuccess = false } = {}) {
    setActionError(null);
    try {
      const updated = await actionFn();
      setActionMessage("Saved.");
      upsertCandidate(updated);
      if (closeOnSuccess) {
        setSelectedId(null);
        await reload();
      }
    } catch (error) {
      setActionError(error.message || "Action failed");
    }
  }

  function toggleSelected(candidateId) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(candidateId)) next.delete(candidateId);
      else next.add(candidateId);
      return next;
    });
  }

  function selectAllEligible() {
    setSelectedIds(new Set(bulkEligible.map((c) => c.document_field_extraction_id)));
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  // Confirm-as-extracted only, for the exact selected id list -- no
  // corrections, no promotion. Promotion stays the existing separate
  // per-candidate action; nothing here ever calls it.
  // MWO-LTSA-BULK-TIMEOUT-UX-001 -- a client-side timeout/network error
  // on a mutation request does NOT prove the server transaction never
  // committed (observed for real: a 540-candidate bulk review committed
  // ~22s server-side, after the client's own 15s abort had already
  // fired and reported failure). Before ever telling a human "failed",
  // re-fetch the authoritative PENDING_REVIEW set (read-only) and check
  // whether the submitted ids are still in it. If none of them are
  // still pending, the mutation demonstrably committed despite the
  // ambiguous client-side outcome. This NEVER re-submits the mutation
  // itself -- only a GET.
  async function reconcileAfterAmbiguousResult(submittedIds) {
    const fresh = await getHistoricalReviewCandidates({ status: "PENDING_REVIEW" });
    const stillPendingIds = new Set(fresh.map((c) => c.document_field_extraction_id));
    const notCommittedIds = submittedIds.filter((id) => stillPendingIds.has(id));
    return { committed: notCommittedIds.length === 0, notCommittedCount: notCommittedIds.length };
  }

  async function handleBulkReview() {
    if (bulkSubmitting) return; // double-submit guard
    setBulkSubmitting(true);
    setBulkError(null);
    const ids = Array.from(selectedIds);
    try {
      const result = await bulkReviewHistoricalReviewCandidates(ids);
      setBulkResult(result);
      setBulkConfirmOpen(false);
      setSelectedIds(new Set());
    } catch (error) {
      try {
        const { committed } = await reconcileAfterAmbiguousResult(ids);
        if (committed) {
          setBulkResult({ reviewed_count: ids.length });
          setBulkConfirmOpen(false);
          setSelectedIds(new Set());
        } else {
          setBulkError(error.message || "Bulk review failed");
        }
      } catch {
        // Reconciliation itself failed (e.g. also a network error) --
        // report the ORIGINAL error, never mask it with a second one,
        // and never assume success without having actually verified it.
        setBulkError(error.message || "Bulk review failed");
      }
    } finally {
      await reload();
      setBulkSubmitting(false);
    }
  }

  // Confirm-as-extracted for the exact server-flagged recovery batch
  // only -- same endpoint as the generic Bulk Review action, same
  // no-correction/no-promotion guarantee, but the id list here is never
  // derived from a filter or a manual selection, only from
  // recovery_batch_eligible === true.
  async function handleRecoveryReview() {
    if (recoverySubmitting) return; // double-submit guard
    setRecoverySubmitting(true);
    setRecoveryError(null);
    const ids = recoveryEligible.map((c) => c.document_field_extraction_id);
    try {
      const result = await bulkReviewHistoricalReviewCandidates(ids);
      setRecoveryResult(result);
      setRecoveryConfirmOpen(false);
    } catch (error) {
      try {
        const { committed } = await reconcileAfterAmbiguousResult(ids);
        if (committed) {
          setRecoveryResult({ reviewed_count: ids.length });
          setRecoveryConfirmOpen(false);
        } else {
          setRecoveryError(error.message || "Historical PM recovery review failed");
        }
      } catch {
        setRecoveryError(error.message || "Historical PM recovery review failed");
      }
    } finally {
      await reload();
      await loadRecoveryStatus(); // reviewing changes reviewed_count/promotion_ready
      setRecoverySubmitting(false);
    }
  }

  // Terminal promotion of the server-derived recovery batch. Same
  // ambiguous-outcome handling as handleRecoveryReview/handleBulkReview
  // (069c8326): a request failure is never assumed fatal -- re-fetch the
  // authoritative recovery status and check whether it now shows the
  // batch fully SAVED with nothing left REVIEWED/PENDING before ever
  // reporting failure. Never re-submits the promotion itself.
  async function handlePromoteRecoveryBatch() {
    if (promoteSubmitting) return; // double-submit guard
    setPromoteSubmitting(true);
    setPromoteError(null);
    try {
      const result = await promoteHistoricalPmRecoveryBatch();
      setPromoteResult(result);
      setPromoteConfirmOpen(false);
    } catch (error) {
      try {
        const status = await getHistoricalPmRecoveryStatus();
        const fullyPromoted =
          status && status.target_count > 0 && status.pending_count === 0 &&
          status.reviewed_count === 0 && status.saved_count === status.target_count;
        if (fullyPromoted) {
          setPromoteResult({ promoted_count: status.saved_count });
          setPromoteConfirmOpen(false);
        } else {
          setPromoteError(error.message || "Historical PM recovery promotion failed");
        }
      } catch {
        setPromoteError(error.message || "Historical PM recovery promotion failed");
      }
    } finally {
      await loadRecoveryStatus();
      await reload();
      setPromoteSubmitting(false);
    }
  }

  function handleConfirm() {
    runAction(() => reviewHistoricalReviewCandidate(selected.document_field_extraction_id, {}));
  }

  function handleSaveCorrection() {
    runAction(() =>
      reviewHistoricalReviewCandidate(selected.document_field_extraction_id, {
        reviewedFields: fieldEdits,
        reason: reasonInput,
      })
    );
  }

  function handleResolvePump() {
    runAction(() =>
      reviewHistoricalReviewCandidate(selected.document_field_extraction_id, {
        pumpTagNumber: pumpTagInput,
        reason: reasonInput,
      })
    );
  }

  function handleReject() {
    runAction(() => rejectHistoricalReviewCandidate(selected.document_field_extraction_id, reasonInput), {
      closeOnSuccess: true,
    });
  }

  function handlePromote() {
    runAction(() => promoteHistoricalReviewCandidate(selected.document_field_extraction_id), {
      closeOnSuccess: true,
    });
  }

  if (!canAccess) {
    return (
      <div className="ltsa-historical-review">
        <PageHeader title="Historical Data Review" subtitle="July PM/CMON staging review" />
        <EmptyState
          title="Access restricted"
          description="Historical Data Review is available to SUPERUSER and TAP_ADMIN only."
        />
      </div>
    );
  }

  const columns = [
    { key: "document_field_extraction_id", header: "Candidate" },
    {
      key: "detected_document_type",
      header: "Type",
      render: (value) => TYPE_LABEL[value] || value,
    },
    {
      key: "raw_asset_tag",
      header: "Raw Source Tag",
      render: (_value, item) => displayValue((item.extracted_fields || {}).raw_asset_tag),
    },
    { key: "pump_tag_number", header: "Canonical Pump Tag", render: (value) => displayValue(value) },
    {
      key: "classification",
      header: "Classification",
      render: (_value, item) => classificationBadge(classificationOf(item)),
    },
    { key: "status", header: "Status" },
  ];

  return (
    <div className="ltsa-historical-review">
      <PageHeader
        title="Historical Data Review"
        subtitle="Review, correct, resolve pump matches for, and promote staged July PM/CMON/Finding candidates"
      />

      <div className="ltsa-historical-review-summary" data-testid="historical-review-summary">
        <MetricCard title="Pending Review" value={summary.total} />
        <MetricCard title="Matched" value={summary.matched} />
        <MetricCard title="Incomplete" value={summary.incomplete} />
      </div>

      <div className="ltsa-historical-review-filters">
        <label>
          Type:{" "}
          <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
            <option value="ALL">All</option>
            <option value="HISTORICAL_PM_OCCURRENCE_CANDIDATE">PM</option>
            <option value="HISTORICAL_CMON_READING_CANDIDATE">CMON</option>
            <option value="HISTORICAL_FINDING_CANDIDATE">Finding</option>
          </select>
        </label>
        <label>
          Status:{" "}
          <select value={matchFilter} onChange={(event) => setMatchFilter(event.target.value)}>
            <option value="ALL">All</option>
            <option value="MATCHED">Matched</option>
            <option value="INCOMPLETE">Incomplete</option>
          </select>
        </label>
        <Button onClick={reload}>Refresh</Button>
      </div>

      <div className="ltsa-historical-review-recovery-panel" data-testid="recovery-panel">
        <div className="ltsa-historical-review-bulk-header">
          <strong>Historical PM Recovery</strong>
        </div>
        <p data-testid="recovery-summary">
          Verified candidates: <strong>{recoveryEligible.length}</strong> &nbsp; Excluded pending candidates:{" "}
          <strong>{recoveryExcludedCount}</strong>
        </p>
        <div className="ltsa-historical-review-actions">
          <Button
            onClick={() => setRecoveryConfirmOpen(true)}
            disabled={!recoveryInternallyConsistent}
          >
            Review {recoveryEligible.length} Verified PM
          </Button>
        </div>
        {!recoveryInternallyConsistent && recoveryEligible.length > 0 ? (
          <p className="ltsa-historical-review-error">
            Recovery set is inconsistent (duplicate or missing candidate identity) -- action disabled.
          </p>
        ) : null}
        {recoveryError ? <p className="ltsa-historical-review-error">{recoveryError}</p> : null}
        {recoveryResult ? (
          <p className="ltsa-historical-review-success">
            Historical PM recovery reviewed {recoveryResult.reviewed_count} candidate(s).
          </p>
        ) : null}
      </div>

      <Modal isOpen={recoveryConfirmOpen} onClose={() => setRecoveryConfirmOpen(false)} title="Confirm Historical PM Recovery">
        <p>
          Review exactly <strong>{recoveryEligible.length}</strong> verified historical PM candidates?
        </p>
        <p>
          {recoveryEligible.length} verified &nbsp; {recoveryExcludedCount} excluded (old pending PM, CMON,
          Finding, and any candidate without a verified recovery identity are never included).
        </p>
        <div className="ltsa-historical-review-actions">
          <Button onClick={handleRecoveryReview} disabled={recoverySubmitting || !recoveryInternallyConsistent}>
            {recoverySubmitting ? "Submitting..." : `Confirm Review of ${recoveryEligible.length}`}
          </Button>
          <Button onClick={() => setRecoveryConfirmOpen(false)} disabled={recoverySubmitting}>
            Cancel
          </Button>
        </div>
      </Modal>

      {recoveryStatus && (recoveryStatus.promotion_ready || promoteResult || promoteError) ? (
        <div className="ltsa-historical-review-recovery-panel" data-testid="recovery-promote-panel">
          <div className="ltsa-historical-review-bulk-header">
            <strong>Historical PM Recovery -- Promotion</strong>
          </div>
          {recoveryStatus.promotion_ready ? (
            <>
              <p data-testid="recovery-promote-summary">
                {recoveryStatus.target_count} reviewed PM &nbsp;
                {recoveryStatus.final_pm_current} -&gt; {recoveryStatus.final_pm_projected} final PM
              </p>
              <div className="ltsa-historical-review-actions">
                <Button onClick={() => setPromoteConfirmOpen(true)} disabled={promoteSubmitting}>
                  Promote Verified PM to Final
                </Button>
              </div>
            </>
          ) : null}
          {/* Result/error messages persist even after promotion_ready
              flips to false (expected once nothing is left to promote)
              -- a human must still see the outcome, not have it vanish
              the instant the panel's own readiness recomputes. */}
          {promoteError ? <p className="ltsa-historical-review-error">{promoteError}</p> : null}
          {promoteResult ? (
            <p className="ltsa-historical-review-success">
              Promoted {promoteResult.promoted_count} historical PM candidate(s) to final.
            </p>
          ) : null}
        </div>
      ) : null}

      <Modal isOpen={promoteConfirmOpen} onClose={() => setPromoteConfirmOpen(false)} title="Confirm Historical PM Promotion">
        {recoveryStatus ? (
          <>
            <p>
              Promote exactly <strong>{recoveryStatus.target_count}</strong> verified historical PM candidates to
              final PM occurrences? This is terminal and cannot be undone through this screen.
            </p>
            <p>
              {recoveryStatus.target_count} reviewed PM &nbsp;
              {recoveryStatus.final_pm_current} -&gt; {recoveryStatus.final_pm_projected} final PM
            </p>
          </>
        ) : null}
        <div className="ltsa-historical-review-actions">
          <Button onClick={handlePromoteRecoveryBatch} disabled={promoteSubmitting || !recoveryStatus}>
            {promoteSubmitting ? "Submitting..." : `Confirm Promotion of ${recoveryStatus?.target_count ?? 0}`}
          </Button>
          <Button onClick={() => setPromoteConfirmOpen(false)} disabled={promoteSubmitting}>
            Cancel
          </Button>
        </div>
      </Modal>

      <div className="ltsa-historical-review-bulk-panel" data-testid="bulk-review-panel">
        <div className="ltsa-historical-review-bulk-header">
          <strong>Bulk Review (PM only, confirm-as-extracted)</strong>
          <span data-testid="bulk-review-summary">
            {selectedIds.size} selected of {bulkEligible.length} eligible in current filter
          </span>
        </div>
        <div className="ltsa-historical-review-actions">
          <Button onClick={selectAllEligible} disabled={bulkEligible.length === 0}>
            Select All Filtered PM ({bulkEligible.length})
          </Button>
          <Button onClick={clearSelection} disabled={selectedIds.size === 0}>
            Clear Selection
          </Button>
          <Button onClick={() => setBulkConfirmOpen(true)} disabled={selectedIds.size === 0}>
            Bulk Review Selected ({selectedIds.size})
          </Button>
        </div>
        {selectedIds.size > MAX_BULK_REVIEW_BATCH ? (
          <p className="ltsa-historical-review-error">
            {selectedIds.size} exceeds the maximum bulk review batch size ({MAX_BULK_REVIEW_BATCH}).
          </p>
        ) : null}
        {bulkEligible.length > 0 ? (
          <ul className="ltsa-historical-review-bulk-list">
            {bulkEligible.map((candidate) => {
              const id = candidate.document_field_extraction_id;
              return (
                <li key={id}>
                  <label>
                    <input
                      type="checkbox"
                      aria-label={`select-${id}`}
                      checked={selectedIds.has(id)}
                      onChange={() => toggleSelected(id)}
                    />
                    {id} — {displayValue((candidate.extracted_fields || {}).raw_asset_tag)} /{" "}
                    {displayValue(candidate.pump_tag_number)}
                  </label>
                </li>
              );
            })}
          </ul>
        ) : null}
        {bulkError ? <p className="ltsa-historical-review-error">{bulkError}</p> : null}
        {bulkResult ? (
          <p className="ltsa-historical-review-success">
            Bulk reviewed {bulkResult.reviewed_count} candidate(s).
          </p>
        ) : null}
      </div>

      <Modal isOpen={bulkConfirmOpen} onClose={() => setBulkConfirmOpen(false)} title="Confirm Bulk Review">
        <p>
          You are about to confirm-as-extracted <strong>{selectedIds.size}</strong> PM candidate(s), exactly
          the ones currently selected. No field is corrected and nothing is promoted -- promotion remains a
          separate, per-candidate action.
        </p>
        <div className="ltsa-historical-review-actions">
          <Button onClick={handleBulkReview} disabled={bulkSubmitting || selectedIds.size === 0}>
            {bulkSubmitting ? "Submitting..." : `Confirm Bulk Review of ${selectedIds.size}`}
          </Button>
          <Button onClick={() => setBulkConfirmOpen(false)} disabled={bulkSubmitting}>
            Cancel
          </Button>
        </div>
      </Modal>

      {loading ? (
        <p>Loading...</p>
      ) : loadError ? (
        <EmptyState title="Unable to load candidates" description={loadError} />
      ) : filtered.length === 0 ? (
        <EmptyState title="No pending candidates" description="Nothing matches the current filters." />
      ) : (
        <Table
          columns={columns}
          data={filtered}
          rowKey="document_field_extraction_id"
          onRowClick={openDetail}
          selectedKey={selectedId}
        />
      )}

      <Modal isOpen={Boolean(selected)} onClose={() => setSelectedId(null)} title="Candidate Detail">
        {selected ? (
          <div className="ltsa-historical-review-detail">
            <p>
              <strong>Source document:</strong> {displayValue(selected.source_document_id)} ({displayValue(selected.source_document_type)})
              {selected.source_page ? ` — page ${selected.source_page}` : ""}
            </p>
            <p>
              <strong>Provenance:</strong> {displayValue(selected.extraction_provider)}
            </p>
            <p>
              <strong>Status:</strong> {selected.status} &nbsp;
              <strong>Classification:</strong> {classificationBadge(classificationOf(selected))}
            </p>
            <p>
              <strong>Raw source tag (immutable):</strong>{" "}
              {displayValue((selected.extracted_fields || {}).raw_asset_tag)} &nbsp;
              <strong>Canonical pump relation:</strong> {displayValue(selected.pump_tag_number)}
            </p>

            <h3>Source (raw extracted) value — immutable</h3>
            <table className="ltsa-historical-review-field-table">
              <tbody>
                {Object.entries(selected.extracted_fields || {}).map(([field, value]) => (
                  <tr key={field}>
                    <td>{field}</td>
                    <td data-testid={`source-value-${field}`}>{displayValue(value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h3>Proposed canonical value (correctable)</h3>
            <table className="ltsa-historical-review-field-table">
              <tbody>
                {Object.entries(fieldEdits).map(([field, value]) => (
                  <tr key={field}>
                    <td>{field}</td>
                    <td>
                      <input
                        aria-label={`edit-${field}`}
                        value={value === null || value === undefined ? "" : value}
                        onChange={(event) =>
                          setFieldEdits((current) => ({ ...current, [field]: event.target.value }))
                        }
                      />
                      <Button
                        onClick={() => setFieldEdits((current) => ({ ...current, [field]: null }))}
                      >
                        Mark N/A
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <label>
              Reason (required for any correction, resolution, or rejection):
              <input
                aria-label="reason"
                value={reasonInput}
                onChange={(event) => setReasonInput(event.target.value)}
              />
            </label>

            <div className="ltsa-historical-review-actions">
              <Button onClick={handleConfirm}>Confirm As Extracted</Button>
              <Button onClick={handleSaveCorrection}>Save Correction</Button>
            </div>

            <h3>Resolve Pump Match</h3>
            <input
              aria-label="pump-tag-input"
              value={pumpTagInput}
              onChange={(event) => setPumpTagInput(event.target.value)}
            />
            <Button onClick={handleResolvePump}>Resolve Pump Match</Button>

            <div className="ltsa-historical-review-actions">
              <Button onClick={handleReject}>Reject</Button>
              <Button
                onClick={handlePromote}
                disabled={selected.status !== "REVIEWED" || !selected.pump_tag_number || !PROMOTABLE_TYPES.has(selected.detected_document_type)}
              >
                Promote
              </Button>
            </div>

            {actionError ? <p className="ltsa-historical-review-error">{actionError}</p> : null}
            {actionMessage ? <p className="ltsa-historical-review-success">{actionMessage}</p> : null}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
