import { useEffect, useMemo, useState } from "react";
import { Badge, Button, EmptyState, MetricCard, Modal, PageHeader, Table } from "../../../design-system";
import {
  getHistoricalReviewCandidates,
  reviewHistoricalReviewCandidate,
  rejectHistoricalReviewCandidate,
  promoteHistoricalReviewCandidate,
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

function pumpMatchOf(candidate) {
  // No literal "match status" column is persisted on document_field_
  // extraction (only pump_tag_number, nullable) -- a resolved tag means
  // the orchestrator's own EXACT_MATCH (or a human's later resolution);
  // an unresolved one needs review, never guessed as one or the other.
  return candidate.pump_tag_number ? "MATCHED" : "NEEDS_RESOLUTION";
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

  useEffect(() => {
    if (canAccess) reload();
    else setLoading(false);
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
      if (matchFilter !== "ALL" && pumpMatchOf(candidate) !== matchFilter) return false;
      return true;
    });
  }, [pending, typeFilter, matchFilter]);

  const summary = useMemo(() => {
    let matched = 0;
    let needsResolution = 0;
    for (const candidate of pending) {
      if (pumpMatchOf(candidate) === "MATCHED") matched += 1;
      else needsResolution += 1;
    }
    return { total: pending.length, matched, needsResolution };
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
    { key: "pump_tag_number", header: "Pump Tag", render: (value) => displayValue(value) },
    {
      key: "match",
      header: "Pump Match",
      render: (_value, item) =>
        pumpMatchOf(item) === "MATCHED" ? (
          <Badge variant="success">Matched</Badge>
        ) : (
          <Badge variant="warning">Needs Resolution</Badge>
        ),
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
        <MetricCard title="Pump Matched" value={summary.matched} />
        <MetricCard title="Needs Pump Resolution" value={summary.needsResolution} />
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
          Pump Match:{" "}
          <select value={matchFilter} onChange={(event) => setMatchFilter(event.target.value)}>
            <option value="ALL">All</option>
            <option value="MATCHED">Matched</option>
            <option value="NEEDS_RESOLUTION">Needs Resolution</option>
          </select>
        </label>
        <Button onClick={reload}>Refresh</Button>
      </div>

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
              <strong>Pump Match:</strong> {pumpMatchOf(selected) === "MATCHED" ? "Matched" : "Needs Resolution"}
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
