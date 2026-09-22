import { useEffect, useRef, useState } from "react";
import { AuthProvider, useAuth } from "../ltsa/auth/AuthContext";
import LoginView from "../ltsa/pages/LoginView";
import {
  startWorkforcePilotRun,
  startNexaReportRun,
  getWorkforcePilotRun,
  reviewWorkforcePilotRun,
} from "../../api/ai5rClient";
import "./WorkforceWorkspace.css";

const LABELS = {
  RUNNING: "Running",
  AWAITING_REVIEW: "Awaiting Review",
  COMPLETED: "Approved",
  REJECTED: "Rejected",
  FAILED: "Failed",
};

const DISCLAIMER = "Draft approved. No external action was performed.";
const NEXA_DISCLAIMER = "Approval confirms the report draft only. It does not publish, send, or modify LTSA operational data.";

function errorMessage(error) {
  return ({
    401: "Your session has expired. Sign in again.",
    403: "You do not have permission to perform this action.",
    404: "This mission could not be found for your organization.",
    409: "This mission has already changed. Refresh its current status.",
    422: "The request could not be accepted. Refresh the mission before continuing.",
  })[error?.status] || "The request could not be confirmed. Check your connection and refresh the mission. No automatic retry was made.";
}

function ReviewDialog({ decision, version, busy, onClose, onSubmit }) {
  const ref = useRef(null);
  const [note, setNote] = useState("");
  useEffect(() => { ref.current.showModal(); }, []);
  const approve = decision === "APPROVE";
  return (
    <dialog
      ref={ref}
      className="wf-dialog"
      aria-labelledby="wf-confirm-title"
      onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }}
    >
      <h2 id="wf-confirm-title">{approve ? "Approve this draft?" : "Reject this draft?"}</h2>
      <p>Draft Version v{version}</p>
      <p>
        {approve
          ? "This marks the current draft version as approved. No external action, publishing, email, message, or delivery will occur."
          : "This closes the current mission as rejected."}
      </p>
      {!approve && (
        <label>
          Review note (optional)
          <textarea maxLength={1000} value={note} disabled={busy} onChange={(event) => setNote(event.target.value)} />
        </label>
      )}
      <div className="wf-actions">
        <button autoFocus disabled={busy} onClick={onClose}>Cancel</button>
        <button className="wf-primary" disabled={busy} onClick={() => onSubmit(note)}>
          {busy ? "Submitting..." : approve ? "Approve Draft" : "Reject Draft"}
        </button>
      </div>
    </dialog>
  );
}

export function WorkforcePilot({ session, onLogout }) {
  const storageKey = `ai5r.workforce.reference:${session.organization.id}:${session.user.id}`;
  const [reference, setReference] = useState(() => {
    const runId = new URLSearchParams(window.location.search).get("run");
    if (runId) return { runId };
    try { return JSON.parse(sessionStorage.getItem(storageKey)) || {}; } catch { return {}; }
  });
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [review, setReview] = useState(null);
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const [activeEmployee, setActiveEmployee] = useState("doc");
  const [startDate, setStartDate] = useState("2026-01-01");
  const [endDate, setEndDate] = useState("2026-01-31");
  const [area, setArea] = useState("");

  const lock = useRef(false);
  const permissions = session.permissions;
  const canExecute = !Array.isArray(permissions) || permissions.includes("workforce.pilot.execute");
  const canReview = !Array.isArray(permissions) || permissions.includes("workforce.pilot.review");

  function remember(value) {
    // Only identifiers; never draft content. Scope to authenticated identity.
    sessionStorage.setItem(storageKey, JSON.stringify(value));
    const url = new URL(window.location.href);
    if (value.runId) url.searchParams.set("run", value.runId);
    else url.searchParams.delete("run");
    window.history.replaceState({}, "", url);
    setReference(value);
  }

  useEffect(() => {
    if (!reference.runId) return;
    let cancelled = false;
    lock.current = true;
    setBusy("refresh");
    getWorkforcePilotRun(reference.runId).then((value) => {
      if (!cancelled) {
        setRun(value);
        if (value?.mission_type === "LTSA_OPERATIONAL_REPORT_DRAFT") {
          setActiveEmployee("nexa");
        }
        setNeedsRefresh(false);
        setError("");
      }
    }).catch((err) => { if (!cancelled) { setError(errorMessage(err)); setNeedsRefresh(true); } })
      .finally(() => { if (!cancelled) { lock.current = false; setBusy(""); } });
    return () => { cancelled = true; };
  }, [reference.runId]);

  async function refresh() {
    if (lock.current || !reference.runId) return;
    lock.current = true; setBusy("refresh"); setError("");
    try {
      const val = await getWorkforcePilotRun(reference.runId);
      setRun(val);
      if (val?.mission_type === "LTSA_OPERATIONAL_REPORT_DRAFT") {
        setActiveEmployee("nexa");
      }
      setNeedsRefresh(false);
    } catch (err) { setError(errorMessage(err)); setNeedsRefresh(true); }
    finally { lock.current = false; setBusy(""); }
  }

  async function start() {
    if (lock.current || !canExecute || needsRefresh || (reference.runId && !run) || ["RUNNING", "AWAITING_REVIEW"].includes(run?.status)) return;
    lock.current = true; setBusy("start"); setError("");
    try {
      const idempotencyKey = reference.idempotencyKey || crypto.randomUUID();
      remember({ idempotencyKey });
      const value = await startWorkforcePilotRun(idempotencyKey);
      setRun(value);
      remember({ runId: value.run_id });
    } catch (err) { setError(errorMessage(err)); }
    finally { lock.current = false; setBusy(""); }
  }

  async function startNexa() {
    if (lock.current || !canExecute || needsRefresh || (reference.runId && !run) || ["RUNNING", "AWAITING_REVIEW"].includes(run?.status)) return;
    lock.current = true; setBusy("start"); setError("");
    try {
      const idempotencyKey = reference.idempotencyKey || crypto.randomUUID();
      remember({ idempotencyKey });
      const value = await startNexaReportRun({
        startDate,
        endDate,
        area: area.trim() || undefined,
        idempotencyKey,
      });
      setRun(value);
      remember({ runId: value.run_id });
    } catch (err) { setError(errorMessage(err)); }
    finally { lock.current = false; setBusy(""); }
  }

  async function submitReview(note) {
    if (lock.current || !canReview || needsRefresh || run?.status !== "AWAITING_REVIEW" || !review) return;
    lock.current = true; setBusy("review"); setError("");
    try { setRun(await reviewWorkforcePilotRun(run.run_id, review.decision, review.version, note)); }
    catch (err) { setError(errorMessage(err)); setNeedsRefresh(true); }
    finally { setReview(null); lock.current = false; setBusy(""); }
  }

  const status = busy === "start" ? "RUNNING" : run?.status;
  const startDisabled = Boolean(busy || !canExecute || needsRefresh || (reference.runId && !run) || ["RUNNING", "AWAITING_REVIEW"].includes(status));
  const reviewable = run?.status === "AWAITING_REVIEW" && Number.isInteger(run.draft_version) && run.draft_version === run.draft?.version;

  const isNexa = activeEmployee === "nexa" || run?.mission_type === "LTSA_OPERATIONAL_REPORT_DRAFT";

  return (
    <div className="wf-shell">
      <aside className="wf-sidebar">
        <a href="/" className="wf-brand">
          <img src="/branding/AI5R-logo.svg" alt="" />
          AI5R
        </a>
        <span>WORKSPACES</span>
        <nav aria-label="Workspaces">
          <a href="/ltsa">LTSA Engineering</a>
          <a href="/workforce" aria-current="page">Workforce</a>
        </nav>
        <p>Controlled AI Employee Pilot</p>
      </aside>
      <div className="wf-body">
        <header className="wf-topbar">
          <span>Workforce / {isNexa ? "LTSA Report Analyst (NEXA)" : "Documentation Pilot"}</span>
          <div>
            {session.user.name}
            <button onClick={onLogout} disabled={Boolean(busy)}>Log out</button>
          </div>
        </header>
        <main className="wf-main">
          <div className="wf-heading">
            <div>
              <h1>AI5R Workforce</h1>
              <p>Controlled AI Employee Operations</p>
            </div>
            <div className="wf-tabs" role="tablist">
              <button
                role="tab"
                aria-selected={!isNexa}
                className={`wf-tab ${!isNexa ? "active" : ""}`}
                onClick={() => setActiveEmployee("doc")}
              >
                Documentation Engineer
              </button>
              <button
                role="tab"
                aria-selected={isNexa}
                className={`wf-tab ${isNexa ? "active" : ""}`}
                onClick={() => setActiveEmployee("nexa")}
              >
                NEXA (LTSA Report Analyst)
              </button>
            </div>
          </div>
          {error && <div role="alert" className="wf-error">{error}</div>}
          <div className="wf-grid">
            {isNexa ? (
              <section className="wf-card">
                <div className="wf-eyebrow">AI Employee</div>
                <h2>NEXA</h2>
                <p>Role: LTSA Report Analyst</p>
                <p>Status: {status === "RUNNING" ? "Running" : status === "AWAITING_REVIEW" ? "Awaiting Review" : "Ready"}</p>
                <p>Mission capability: LTSA Operational Report Draft</p>
                <div className="wf-form">
                  <label className="wf-label">
                    From
                    <input
                      type="date"
                      aria-label="From"
                      value={startDate}
                      disabled={Boolean(busy || ["RUNNING", "AWAITING_REVIEW"].includes(status))}
                      onChange={(e) => setStartDate(e.target.value)}
                    />
                  </label>
                  <label className="wf-label">
                    To
                    <input
                      type="date"
                      aria-label="To"
                      value={endDate}
                      disabled={Boolean(busy || ["RUNNING", "AWAITING_REVIEW"].includes(status))}
                      onChange={(e) => setEndDate(e.target.value)}
                    />
                  </label>
                  <label className="wf-label">
                    Area (optional)
                    <input
                      type="text"
                      aria-label="Area"
                      placeholder="e.g. AREA-01"
                      value={area}
                      disabled={Boolean(busy || ["RUNNING", "AWAITING_REVIEW"].includes(status))}
                      onChange={(e) => setArea(e.target.value)}
                    />
                  </label>
                </div>
                <button className="wf-primary" disabled={startDisabled} onClick={startNexa}>
                  {busy === "start" ? "Running..." : "Generate Draft"}
                </button>
                {!canExecute && <p className="wf-muted">Execute permission is required to start a mission.</p>}
              </section>
            ) : (
              <section className="wf-card">
                <div className="wf-eyebrow">AI Employee</div>
                <h2>Documentation Engineer</h2>
                <p>Role: Documentation Engineer</p>
                <p>Status: {status === "RUNNING" ? "Running" : status === "AWAITING_REVIEW" ? "Awaiting Review" : "Ready"}</p>
                <p>Mission capability: Documentation Pilot</p>
                <p className="wf-muted">This pilot uses a controlled synthetic documentation task.</p>
                <button className="wf-primary" disabled={startDisabled} onClick={start}>
                  {busy === "start" ? "Running..." : reference.idempotencyKey ? "Recover start request" : "Start Documentation Mission"}
                </button>
                {!canExecute && <p className="wf-muted">Execute permission is required to start a mission.</p>}
                {reference.idempotencyKey && busy !== "start" && (
                  <p className="wf-muted">The start result is unconfirmed. Recover uses the same request key; it does not create a second mission.</p>
                )}
              </section>
            )}

            <section className="wf-card">
              <div className="wf-eyebrow">Current Mission</div>
              <h2>{isNexa ? "Create LTSA Operational Report" : "Documentation Pilot"}</h2>
              <p role="status" className={`wf-status wf-${status || "idle"}`}>
                {LABELS[status] || (busy === "refresh" ? "Loading mission..." : "No mission loaded")}
              </p>
              {run && (
                <dl>
                  <dt>Run ID</dt>
                  <dd>{run.run_id}</dd>
                  <dt>Mission Type</dt>
                  <dd>{run.mission_type}</dd>
                  {run.period_start && (
                    <>
                      <dt>Period</dt>
                      <dd>{run.period_start} to {run.period_end}</dd>
                    </>
                  )}
                  {run.evidence_sha256 && (
                    <>
                      <dt>Evidence SHA</dt>
                      <dd title={run.evidence_sha256}>{run.evidence_sha256.slice(0, 16)}...</dd>
                    </>
                  )}
                  <dt>Draft Version</dt>
                  <dd>{run.draft_version ? `v${run.draft_version}` : "Not available"}</dd>
                  {run.review && (
                    <>
                      <dt>Reviewed By</dt>
                      <dd>{run.review.reviewer_id}</dd>
                    </>
                  )}
                </dl>
              )}
              {reference.runId && <button disabled={Boolean(busy)} onClick={refresh}>Refresh mission</button>}
              {status === "COMPLETED" && <p className="wf-approved">{isNexa ? NEXA_DISCLAIMER : DISCLAIMER}</p>}
              {status === "FAILED" && (
                <p>{run.safe_error === "Pilot AI execution failed" ? run.safe_error : "Mission failed before a draft was produced."}</p>
              )}
            </section>
          </div>

          {run && (
            <div className="wf-content-grid">
              <section className="wf-card">
                <div className="wf-section-heading">
                  <h2>Generated Draft</h2>
                  {run.draft && <span className="wf-tag">Version v{run.draft.version}</span>}
                </div>
                {run.draft ? <pre className="wf-draft">{run.draft.content}</pre> : <p className="wf-muted">No draft has been produced.</p>}
              </section>
              <section className="wf-card">
                <h2>{isNexa ? "Evidence & Provenance" : "AI Execution Provenance"}</h2>
                <dl>
                  <dt>Provider</dt>
                  <dd>{run.actual_provider ?? "Not available"}</dd>
                  <dt>Model</dt>
                  <dd>{run.actual_model ?? "Not available"}</dd>
                  <dt>Routing Policy</dt>
                  <dd>{run.requested_policy ?? "Not available"}</dd>
                  <dt>Fallback</dt>
                  <dd>{run.fallback_used === true ? "Yes" : run.fallback_used === false ? "No" : "Not available"}</dd>
                  <dt>Runtime</dt>
                  <dd>{typeof run.elapsed_ms === "number" ? `${(run.elapsed_ms / 1000).toFixed(1)} sec` : "Not available"}</dd>
                  {run.evidence_source_domains && (
                    <>
                      <dt>Source Domains</dt>
                      <dd>{run.evidence_source_domains.join(", ")}</dd>
                    </>
                  )}
                  {run.evidence_row_counts && (
                    <>
                      <dt>Row Counts</dt>
                      <dd>{Object.entries(run.evidence_row_counts).map(([d, c]) => `${d}: ${c}`).join("; ")}</dd>
                    </>
                  )}
                </dl>
              </section>
            </div>
          )}

          {reviewable && (
            <section className="wf-review-bar">
              <div>
                <p>Review the current draft version before deciding.</p>
                {isNexa && <p className="wf-disclaimer">{NEXA_DISCLAIMER}</p>}
              </div>
              {canReview ? (
                <div className="wf-actions">
                  <button
                    disabled={Boolean(busy || needsRefresh)}
                    onClick={() => setReview({ decision: "REJECT", version: run.draft_version })}
                  >
                    Reject
                  </button>
                  <button
                    className="wf-primary"
                    disabled={Boolean(busy || needsRefresh)}
                    onClick={() => setReview({ decision: "APPROVE", version: run.draft_version })}
                  >
                    Approve Draft
                  </button>
                </div>
              ) : (
                <p>Review permission is required to approve or reject this draft.</p>
              )}
            </section>
          )}
          {review && (
            <ReviewDialog
              decision={review.decision}
              version={review.version}
              busy={busy === "review"}
              onClose={() => setReview(null)}
              onSubmit={submitReview}
            />
          )}
        </main>
      </div>
    </div>
  );
}

function WorkforceGate() {
  const { status, session, error, login, logout } = useAuth();
  if (status === "checking") return <p role="status">Checking session...</p>;
  if (status !== "authenticated") return <LoginView status={status} error={error} onSubmit={login} />;
  return <WorkforcePilot key={`${session.organization.id}:${session.user.id}`} session={session} onLogout={logout} />;
}

export default function WorkforceWorkspace() {
  return <AuthProvider><WorkforceGate /></AuthProvider>;
}
