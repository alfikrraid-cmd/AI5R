import { useEffect, useMemo, useState } from "react";
import { Badge, Button, EmptyState, PageHeader, Panel } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import {
  getPMOccurrences, getConditionMonitoringReadings,
  batchSubmitPMOccurrences, batchTechnicalReviewPMOccurrences,
  batchSubmitConditionMonitoringReadings, batchTechnicalReviewConditionMonitoringReadings,
} from "../../../api/ai5rClient";
import { mapPMOccurrenceRecord } from "../utils/pmMapping";
import { mapConditionMonitoringReadingRecord } from "../utils/conditionMonitoringMapping";
import { classifyPMOccurrence, classifyConditionMonitoringReading } from "../utils/historicalBatchReviewClassification";
import { useOptionalAuth } from "../auth/AuthContext";
import { can, PERMISSIONS } from "../auth/permissions";

// MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-019 -- a review QUEUE over the
// July 2026 historical-import backlog MWO-018 identified (provenance=
// 'HISTORICAL_IMPORT', source_reference='document_field_extraction:...').
// Convenience only: every action here calls the SAME batch-submit/batch-
// technical-review endpoints, which loop the exact same individual
// submit()/technical_finalize() repository methods PM.jsx/
// ConditionMonitoring.jsx's own single-record review UI already uses --
// no parallel workflow, no DRAFT->FINALIZED shortcut. Classification
// (READY_FOR_REVIEW/NEEDS_ATTENTION) is presentation triage only, never
// approval -- see historicalBatchReviewClassification.js's own header.
const WORKFLOW_OPTIONS = ["DRAFT", "SUBMITTED", "RETURNED_FOR_CORRECTION", "FINALIZED"];
const EVIDENCE_OPTIONS = ["READY_FOR_REVIEW", "NEEDS_ATTENTION"];

function isJulyHistoricalBatchRecord(record) {
  return record.provenance === "HISTORICAL_IMPORT";
}

function evidenceBadgeVariant(evidence) {
  return evidence === "READY_FOR_REVIEW" ? "success" : evidence === "NEEDS_ATTENTION" ? "warning" : "purple";
}

export default function HistoricalBatchReview({ onNavigate }) {
  const [domain, setDomain] = useState("PM");
  const [workflowFilter, setWorkflowFilter] = useState("DRAFT");
  const [evidenceFilter, setEvidenceFilter] = useState("ALL");

  const [pmOccurrences, setPmOccurrences] = useState([]);
  const [cmonReadings, setCmonReadings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [actionResult, setActionResult] = useState(null);
  const [actionPending, setActionPending] = useState(false);

  const authContext = useOptionalAuth();
  const canSubmit = can(authContext?.session, PERMISSIONS.MAINTENANCE_WRITE);
  const canTechnicalReview = can(authContext?.session, PERMISSIONS.MAINTENANCE_TECHNICAL_REVIEW);

  function load() {
    setLoading(true);
    Promise.all([getPMOccurrences(), getConditionMonitoringReadings()])
      .then(([pmRaw, cmonRaw]) => {
        setPmOccurrences(pmRaw.map(mapPMOccurrenceRecord));
        setCmonReadings(cmonRaw.map(mapConditionMonitoringReadingRecord));
        setLoadError(null);
      })
      .catch(() => setLoadError("Historical batch review data could not be loaded."))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  const rows = useMemo(() => {
    const source = domain === "PM" ? pmOccurrences : cmonReadings;
    const classify = domain === "PM" ? classifyPMOccurrence : classifyConditionMonitoringReading;
    return source
      .filter(isJulyHistoricalBatchRecord)
      .map((record) => ({ record, evidence: classify(record) }))
      .filter(({ record }) => workflowFilter === "ALL" || record.workflowStatus === workflowFilter)
      .filter(({ evidence }) => evidenceFilter === "ALL" || evidence === evidenceFilter);
  }, [domain, pmOccurrences, cmonReadings, workflowFilter, evidenceFilter]);

  const counters = useMemo(() => {
    const count = (source, classify) => {
      const draft = source.filter(isJulyHistoricalBatchRecord).filter((r) => r.workflowStatus === "DRAFT");
      const ready = draft.filter((r) => classify(r) === "READY_FOR_REVIEW").length;
      return { ready, needsAttention: draft.length - ready };
    };
    return { pm: count(pmOccurrences, classifyPMOccurrence), cmon: count(cmonReadings, classifyConditionMonitoringReading) };
  }, [pmOccurrences, cmonReadings]);

  // Selection is cleared on domain/filter change -- never carries a
  // stale, no-longer-visible code into a batch action.
  useEffect(() => {
    setSelected(new Set());
  }, [domain, workflowFilter, evidenceFilter]);

  function toggleRow(code) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  // Only currently-visible, eligible (DRAFT) rows -- never a hidden
  // record, never a record outside the DRAFT workflow state for submit.
  function selectVisibleEligible(requiredStatus) {
    setSelected(new Set(rows.filter(({ record }) => record.workflowStatus === requiredStatus).map(({ record }) => record.id)));
  }

  async function runBatchSubmit() {
    setActionPending(true);
    setActionResult(null);
    try {
      const codes = [...selected];
      const fn = domain === "PM" ? batchSubmitPMOccurrences : batchSubmitConditionMonitoringReadings;
      const result = await fn(codes);
      setActionResult({ kind: "submit", ...result });
      setSelected(new Set());
      load();
    } catch (err) {
      setActionResult({ kind: "submit", error: err.message });
    } finally {
      setActionPending(false);
    }
  }

  async function runBatchTechnicalReview(action) {
    setActionPending(true);
    setActionResult(null);
    try {
      const codes = [...selected];
      const fn = domain === "PM" ? batchTechnicalReviewPMOccurrences : batchTechnicalReviewConditionMonitoringReadings;
      const result = await fn(codes, { action, comment: null, recommendation: null });
      setActionResult({ kind: action, ...result });
      setSelected(new Set());
      load();
    } catch (err) {
      setActionResult({ kind: action, error: err.message });
    } finally {
      setActionPending(false);
    }
  }

  function openDetail(record) {
    if (domain === "PM") onNavigate?.("pm", { occurrenceSelectId: record.id });
    else onNavigate?.("cmon", { readingSelectId: record.id });
  }

  const selectedCount = selected.size;

  return (
    <div>
      <PageHeader title="Historical Batch Review" subtitle="LTSA Engineering — July 2026 Historical Import Review Queue" />

      <div style={{ display: "flex", gap: spacing.md, marginBottom: spacing.md }}>
        <Panel>
          <strong>PM</strong> — Ready for Review: {counters.pm.ready} · Needs Attention: {counters.pm.needsAttention}
        </Panel>
        <Panel>
          <strong>CMON</strong> — Ready for Review: {counters.cmon.ready} · Needs Attention: {counters.cmon.needsAttention}
        </Panel>
      </div>

      <div style={{ display: "flex", gap: spacing.md, flexWrap: "wrap", marginBottom: spacing.md }}>
        <select aria-label="Domain" value={domain} onChange={(e) => setDomain(e.target.value)}>
          <option value="PM">PM</option>
          <option value="CMON">Condition Monitoring</option>
        </select>

        <select aria-label="Workflow status" value={workflowFilter} onChange={(e) => setWorkflowFilter(e.target.value)}>
          <option value="ALL">All Workflow States</option>
          {WORKFLOW_OPTIONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select aria-label="Evidence classification" value={evidenceFilter} onChange={(e) => setEvidenceFilter(e.target.value)}>
          <option value="ALL">All Evidence</option>
          {EVIDENCE_OPTIONS.map((e) => (
            <option key={e} value={e}>{e === "READY_FOR_REVIEW" ? "Ready for Review" : "Needs Attention"}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <Panel><p>Loading historical batch review data...</p></Panel>
      ) : loadError ? (
        <Panel><p role="alert">{loadError}</p></Panel>
      ) : rows.length === 0 ? (
        <EmptyState title="No records match" description="Adjust the domain, workflow, or evidence filter." />
      ) : (
        <>
          <div style={{ display: "flex", gap: spacing.sm, marginBottom: spacing.sm, alignItems: "center" }}>
            <Button onClick={() => selectVisibleEligible("DRAFT")}>Select Visible Eligible (DRAFT)</Button>
            <Button onClick={() => selectVisibleEligible("SUBMITTED")}>Select Visible Eligible (SUBMITTED)</Button>
            <Button onClick={() => setSelected(new Set())}>Clear Selection</Button>
            <span style={{ color: colors.textMuted }}>{selectedCount} selected</span>
          </div>

          <div style={{ display: "flex", gap: spacing.sm, marginBottom: spacing.md, flexWrap: "wrap" }}>
            {canSubmit && (
              <Button disabled={selectedCount === 0 || actionPending} onClick={runBatchSubmit}>
                Batch Submit ({selectedCount})
              </Button>
            )}
            {canTechnicalReview && (
              <>
                <Button disabled={selectedCount === 0 || actionPending} onClick={() => runBatchTechnicalReview("ACKNOWLEDGE")}>
                  Batch Acknowledge ({selectedCount})
                </Button>
                <Button disabled={selectedCount === 0 || actionPending} onClick={() => runBatchTechnicalReview("APPROVE")}>
                  Batch Technically Approve ({selectedCount})
                </Button>
                <Button disabled={selectedCount === 0 || actionPending} onClick={() => runBatchTechnicalReview("RETURN")}>
                  Batch Return for Correction ({selectedCount})
                </Button>
              </>
            )}
          </div>

          {actionResult && (
            <Panel>
              {actionResult.error ? (
                <p role="alert">{actionResult.error}</p>
              ) : (
                <p data-testid="batch-action-result">
                  {actionResult.kind}: succeeded={actionResult.succeeded?.length ?? 0}, skipped={actionResult.skipped?.length ?? 0}, failed={actionResult.failed?.length ?? 0}
                </p>
              )}
            </Panel>
          )}

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th></th>
                  <th>Record</th>
                  <th>Pump</th>
                  <th>Date</th>
                  <th>{domain === "PM" ? "Activities" : "Measurement Summary"}</th>
                  <th>{domain === "PM" ? "Finding" : "Leak"}</th>
                  <th>Source</th>
                  <th>Workflow</th>
                  <th>Evidence</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ record, evidence }) => (
                  <tr key={record.id}>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={`Select ${record.id}`}
                        checked={selected.has(record.id)}
                        onChange={() => toggleRow(record.id)}
                      />
                    </td>
                    <td>{record.id}</td>
                    <td>{record.equipmentTag}</td>
                    <td>{domain === "PM" ? record.occurrenceDate : record.readingDate}</td>
                    <td>
                      {domain === "PM"
                        ? `${(record.activities ?? []).filter((a) => a?.done).length} done`
                        : record.mechsealTempDe != null || record.mechsealTempNde != null
                          ? `Mechseal ${record.mechsealTempDe ?? "—"}/${record.mechsealTempNde ?? "—"} °C`
                          : "No measurement"}
                    </td>
                    <td>{domain === "PM" ? (record.finding || "—") : (record.leakDe || record.leakNde ? "Leak" : "No leak recorded")}</td>
                    <td>{record.sourceReference ?? record.provenance}</td>
                    <td>{record.workflowStatus}</td>
                    <td>{evidence ? <Badge variant={evidenceBadgeVariant(evidence)}>{evidence === "READY_FOR_REVIEW" ? "Ready" : "Needs Attention"}</Badge> : "—"}</td>
                    <td>
                      <Button onClick={() => openDetail(record)}>Open</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
