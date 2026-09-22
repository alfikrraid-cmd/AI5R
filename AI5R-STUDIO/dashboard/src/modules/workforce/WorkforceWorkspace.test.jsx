import "@testing-library/jest-dom/vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WorkforcePilot } from "./WorkforceWorkspace";
import { storeSession, onUnauthorized, startWorkforcePilotRun, getWorkforcePilotRun, reviewWorkforcePilotRun } from "../../api/ai5rClient";
import ApplicationRouter from "../../platform/ApplicationRouter";
import PlatformProvider from "../../platform/PlatformProvider";

const session = { user: { id: "user-test", name: "Reviewer" }, organization: { id: "org-test" }, permissions: ["workforce.pilot.execute", "workforce.pilot.review"] };
const storageKey = "ai5r.workforce.reference:org-test:user-test";
const baseRun = {
  run_id: "run-test", mission_type: "WORKFORCE_TEXT_DOCUMENTATION_PILOT", status: "AWAITING_REVIEW",
  requested_policy: "DAHONO_PRIMARY", actual_provider: "DAHONO", actual_model: "dahono/test-model",
  fallback_used: false, elapsed_ms: 52300, draft_version: 7,
  draft: { version: 7, content: "First line\n  <script>unsafe()</script>\nLast line" }, review: null,
};
let current;
let fetchMock;
const response = (body, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
function deferred() { let resolve; const promise = new Promise((r) => { resolve = r; }); return { promise, resolve }; }
function renderPilot(permissions = session.permissions) { return render(<WorkforcePilot session={{ ...session, permissions }} onLogout={vi.fn()} />); }
async function loadRun(overrides = {}, permissions) {
  current = { ...baseRun, ...overrides };
  sessionStorage.setItem(storageKey, JSON.stringify({ runId: current.run_id }));
  renderPilot(permissions);
  await screen.findByText(current.run_id);
  await waitFor(() => expect(screen.getByRole("button", { name: "Refresh mission" })).toBeEnabled());
}
function posts() { return fetchMock.mock.calls.filter(([, options]) => options?.method === "POST"); }
beforeEach(() => {
  current = structuredClone(baseRun);
  window.history.replaceState({}, "", "/workforce");
  localStorage.clear(); sessionStorage.clear(); onUnauthorized(null);
  // jsdom does not implement the native dialog top layer.
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", { configurable: true, value: function () { this.setAttribute("open", ""); } });
  fetchMock = vi.fn(async (url, options) => {
    if (String(url).endsWith("/review")) {
      const body = JSON.parse(options.body);
      current = { ...current, status: body.decision === "APPROVE" ? "COMPLETED" : "REJECTED", review: { reviewer_id: "server-reviewer" } };
    }
    return response(current);
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Workforce bounded pilot", () => {
  it("renders the authenticated /workforce route through the existing router", async () => {
    storeSession({ token: "mock-session" });
    fetchMock.mockResolvedValue(response({ user: { id: "user-test", username: "Reviewer" }, organization: { id: "org-test", code: "TEST" }, permissions: session.permissions }));
    render(<PlatformProvider><ApplicationRouter /></PlatformProvider>);
    expect(await screen.findByRole("heading", { name: "AI5R Workforce" })).toBeVisible();
    expect(screen.queryByText("AI5R STUDIO")).not.toBeInTheDocument();
  });
  it("shows one employee, start CTA, and no prompt, upload or invented metrics", () => {
    const { container } = renderPilot();
    expect(screen.getByRole("heading", { name: "Documentation Engineer" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Start Documentation Mission" })).toBeEnabled();
    expect(container.querySelector("textarea,input[type=file],input[type=text]")).toBeNull();
    expect(screen.queryByText(/Success Rate|Hours Saved|Employees Online/)).toBeNull();
  });
  it("starts at the pilot endpoint with only idempotency key and prevents double start", async () => {
    const pending = deferred(); fetchMock.mockReturnValueOnce(pending.promise);
    renderPilot();
    const button = screen.getByRole("button", { name: "Start Documentation Mission" });
    fireEvent.click(button); fireEvent.click(button);
    expect(posts()).toHaveLength(1);
    expect(screen.getByRole("status")).toHaveTextContent("Running");
    expect(button).toBeDisabled();
    const [url, options] = posts()[0];
    expect(url).toMatch(/\/api\/workforce\/pilot\/runs$/);
    expect(JSON.parse(options.body)).toEqual({ idempotency_key: expect.stringMatching(/^[A-Za-z0-9_-]{1,128}$/) });
    await act(async () => pending.resolve(response(current)));
    expect(await screen.findByText("Awaiting Review", { selector: ".wf-status" })).toBeVisible();
  });
  it("renders persisted draft as text, exact version, provenance and runtime", async () => {
    await loadRun();
    expect(screen.getByText("Version v7")).toBeVisible();
    expect(document.querySelector(".wf-draft").textContent).toBe(baseRun.draft.content);
    expect(document.querySelector(".wf-draft script")).toBeNull();
    for (const value of ["DAHONO", "dahono/test-model", "DAHONO_PRIMARY", "No", "52.3 sec", baseRun.mission_type]) expect(screen.getByText(value)).toBeVisible();
  });
  it("renders actual fallback provider truthfully", async () => {
    await loadRun({ actual_provider: "OTHER_PROVIDER", actual_model: "other/model", fallback_used: true });
    expect(screen.getByText("OTHER_PROVIDER")).toBeVisible();
    expect(screen.getByText("other/model")).toBeVisible();
    expect(screen.getByText("Yes")).toBeVisible();
    expect(screen.queryByText("DAHONO", { exact: true })).toBeNull();
  });
  it.each(["RUNNING", "COMPLETED", "REJECTED", "FAILED"])("hides review controls for %s", async (status) => {
    await loadRun({ status });
    expect(screen.queryByRole("button", { name: "Approve Draft" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Reject" })).toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent(({ RUNNING: "Running", COMPLETED: "Approved", REJECTED: "Rejected", FAILED: "Failed" })[status]);
    if (status === "COMPLETED") expect(screen.getByText("Draft approved. No external action was performed.")).toBeVisible();
  });
  it("requires confirmation, sends exact version without identity, and prevents concurrent reviews", async () => {
    await loadRun();
    fireEvent.click(screen.getByRole("button", { name: "Approve Draft" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("heading", { name: "Approve this draft?" })).toBeVisible();
    expect(within(dialog).getByText(/No external action, publishing/)).toBeVisible();
    expect(posts()).toHaveLength(0);
    const pending = deferred(); fetchMock.mockReturnValueOnce(pending.promise);
    const confirm = within(dialog).getByRole("button", { name: "Approve Draft" });
    fireEvent.click(confirm); fireEvent.click(confirm);
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(posts()).toHaveLength(1);
    expect(posts()[0][0]).toMatch(/\/run-test\/review$/);
    expect(JSON.parse(posts()[0][1].body)).toEqual({ decision: "APPROVE", draft_version: 7 });
    expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeDisabled();
    await act(async () => pending.resolve(response({ ...current, status: "COMPLETED", review: { reviewer_id: "server-reviewer" } })));
    expect(screen.getByRole("status")).toHaveTextContent("Approved");
    expect(screen.getByText("server-reviewer")).toBeVisible();
    expect(screen.getByText("Draft approved. No external action was performed.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Approve Draft" })).toBeNull();
  });
  it("rejects with exact version and supported optional note", async () => {
    await loadRun();
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("This closes the current mission as rejected.")).toBeVisible();
    fireEvent.change(within(dialog).getByRole("textbox"), { target: { value: "Revise wording" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Reject Draft" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Rejected"));
    expect(JSON.parse(posts()[0][1].body)).toEqual({ decision: "REJECT", draft_version: 7, note: "Revise wording" });
    expect(screen.queryByRole("button", { name: "Reject" })).toBeNull();
  });
  it("cancel does not submit any review", async () => {
    await loadRun(); fireEvent.click(screen.getByRole("button", { name: "Approve Draft" }));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).toBeNull(); expect(posts()).toHaveLength(0);
  });
  it.each(["Pilot AI execution failed", "Traceback secret debug payload"])("handles failed safe_error without exposing debug: %s", async (safe_error) => {
    await loadRun({ status: "FAILED", draft: null, draft_version: null, safe_error });
    expect(screen.getByText(safe_error === "Pilot AI execution failed" ? safe_error : "Mission failed before a draft was produced.")).toBeVisible();
    expect(screen.queryByText(/Traceback/)).toBeNull();
  });
  it.each([[401, "Your session has expired"], [403, "You do not have permission"], [409, "This mission has already changed"], [422, "The request could not be accepted"], [500, "The request could not be confirmed"]])("handles HTTP %s safely without retry", async (status, message) => {
    fetchMock.mockResolvedValue(response({ detail: "secret debug payload" }, status));
    renderPilot(); fireEvent.click(screen.getByRole("button", { name: "Start Documentation Mission" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.queryByText(/secret debug payload/)).toBeNull(); expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it("recovers an ambiguous start using the same key after remount, never automatically", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("network private details"));
    const view = renderPilot(); fireEvent.click(screen.getByRole("button", { name: "Start Documentation Mission" }));
    await screen.findByRole("alert");
    const first = JSON.parse(posts()[0][1].body);
    view.unmount(); renderPilot();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Recover start request" }));
    await screen.findByText("Awaiting Review", { selector: ".wf-status" });
    expect(JSON.parse(posts()[1][1].body)).toEqual(first);
  });
  it("refreshes canonical terminal state after a stale review conflict", async () => {
    await loadRun(); fireEvent.click(screen.getByRole("button", { name: "Approve Draft" }));
    fetchMock.mockResolvedValueOnce(response({}, 409));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Approve Draft" }));
    await screen.findByRole("alert");
    expect(screen.getByRole("button", { name: "Approve Draft" })).toBeDisabled();
    expect(posts()).toHaveLength(1);
    current = { ...current, status: "REJECTED" };
    fireEvent.click(screen.getByRole("button", { name: "Refresh mission" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Rejected"));
  });
  it("restores run through GET and never stores draft content", async () => {
    const spy = vi.spyOn(Storage.prototype, "setItem");
    renderPilot(); fireEvent.click(screen.getByRole("button", { name: "Start Documentation Mission" }));
    await screen.findByText("Awaiting Review", { selector: ".wf-status" });
    expect(sessionStorage.getItem(storageKey)).toBe(JSON.stringify({ runId: "run-test" }));
    expect(localStorage.length).toBe(0);
    expect(spy.mock.calls.every(([, value]) => !value.includes("First line"))).toBe(true);
    cleanup(); fetchMock.mockClear(); renderPilot();
    await screen.findByText("run-test");
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/runs\/run-test$/);
    expect(posts()).toHaveLength(0);
  });
  it("supports known run URL for an authenticated reviewer", async () => {
    window.history.replaceState({}, "", "/workforce?run=run-test"); renderPilot(["workforce.pilot.review"]);
    await screen.findByText("run-test");
    expect(screen.getByRole("button", { name: "Start Documentation Mission" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Approve Draft" })).toBeEnabled();
  });
  it("uses explicit execute and review permissions independently, never SUPERUSER as Chief", async () => {
    await loadRun({}, ["workforce.pilot.execute"]);
    expect(screen.queryByRole("button", { name: "Approve Draft" })).toBeNull();
    cleanup(); sessionStorage.clear();
    render(<WorkforcePilot session={{ ...session, permissions: [], role: "SUPERUSER" }} />);
    expect(screen.getByRole("button", { name: "Start Documentation Mission" })).toBeDisabled();
  });
  it("leaves server as authority if permission list is absent", () => {
    render(<WorkforcePilot session={{ ...session, permissions: undefined }} />);
    expect(screen.getByRole("button", { name: "Start Documentation Mission" })).toBeEnabled();
  });
  it("blocks review of inconsistent draft versions", async () => {
    await loadRun({ draft_version: 8 });
    expect(screen.queryByRole("button", { name: "Approve Draft" })).toBeNull();
  });
  it("does not create a run if persisting the recovery key fails", async () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("storage unavailable"); });
    renderPilot(); fireEvent.click(screen.getByRole("button", { name: "Start Documentation Mission" }));
    await screen.findByRole("alert"); expect(fetchMock).not.toHaveBeenCalled();
  });
  it("retains navigation to LTSA and the platform", () => {
    renderPilot(); expect(screen.getByRole("link", { name: "LTSA Engineering" })).toHaveAttribute("href", "/ltsa");
    expect(screen.getByRole("link", { name: "AI5R" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Workforce" })).toHaveAttribute("aria-current", "page");
  });
  it("does not start a second mission while the persisted run is running", async () => {
    await loadRun({ status: "RUNNING", draft: null, draft_version: null });
    fireEvent.click(screen.getByRole("button", { name: "Start Documentation Mission" }));
    expect(posts()).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Start Documentation Mission" })).toBeDisabled();
  });
  it("requires refresh after an ambiguous review failure and does not retry", async () => {
    await loadRun(); fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    fetchMock.mockRejectedValueOnce(new TypeError("private connection details"));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Reject Draft" }));
    await screen.findByRole("alert");
    expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Approve Draft" })).toBeDisabled();
    expect(posts()).toHaveLength(1);
  });
  it("does not silently replace an inaccessible recovered run", async () => {
    sessionStorage.setItem(storageKey, JSON.stringify({ runId: "missing-run" }));
    fetchMock.mockResolvedValue(response({}, 404)); renderPilot();
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be found");
    expect(screen.getByRole("button", { name: "Start Documentation Mission" })).toBeDisabled();
    expect(posts()).toHaveLength(0);
  });
  it("does not restore another user's lightweight run reference", () => {
    sessionStorage.setItem("ai5r.workforce.reference:other-org:other-user", JSON.stringify({ runId: "other-run" }));
    renderPilot(); expect(fetchMock).not.toHaveBeenCalled();
  });
  it("uses the canonical authenticated transport for all three pilot endpoints", async () => {
    storeSession({ token: "mock-session" });
    await startWorkforcePilotRun("test-key");
    await getWorkforcePilotRun("run/test");
    await reviewWorkforcePilotRun("run/test", "REJECT", 7);
    for (const [, options] of fetchMock.mock.calls) expect(options.headers.Authorization).toBe("Bearer mock-session");
    expect(fetchMock.mock.calls[1][0]).toMatch(/runs\/run%2Ftest$/);
    expect(fetchMock.mock.calls[2][0]).toMatch(/runs\/run%2Ftest\/review$/);
    expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual({ decision: "REJECT", draft_version: 7 });
  });
  it("clears canonical authentication on pilot 401", async () => {
    const unauthorized = vi.fn(); onUnauthorized(unauthorized);
    storeSession({ token: "mock-expired-session" });
    fetchMock.mockResolvedValue(response({}, 401));
    await expect(getWorkforcePilotRun("run-test")).rejects.toMatchObject({ status: 401 });
    expect(localStorage.getItem("ai5r.ltsa.session")).toBeNull();
    expect(unauthorized).toHaveBeenCalledTimes(1);
  });
  it("allows a synchronous request beyond the default 15 second timeout", async () => {
    vi.useFakeTimers();
    try {
      const pending = deferred(); fetchMock.mockReturnValueOnce(pending.promise);
      const request = startWorkforcePilotRun("long-request");
      await vi.advanceTimersByTimeAsync(60000);
      expect(fetchMock.mock.calls[0][1].signal.aborted).toBe(false);
      pending.resolve(response(current)); await request;
      expect(fetchMock).toHaveBeenCalledTimes(1);
    } finally { vi.useRealTimers(); }
  });
  it("renders NEXA employee card with period inputs and Generate Draft CTA", async () => {
    const { container } = renderPilot();
    fireEvent.click(screen.getByRole("tab", { name: "NEXA (LTSA Report Analyst)" }));
    expect(await screen.findByRole("heading", { name: "NEXA" })).toBeVisible();
    expect(screen.getByText("Role: LTSA Report Analyst")).toBeVisible();
    expect(screen.getByRole("button", { name: "Generate Draft" })).toBeEnabled();
    expect(screen.getByLabelText("From")).toHaveValue("2026-01-01");
    expect(screen.getByLabelText("To")).toHaveValue("2026-01-31");
    // Ensure no unauthorized publish / send / external action buttons exist
    expect(screen.queryByRole("button", { name: /Send|Publish|WhatsApp|Email/i })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Generate Draft" }));
    await waitFor(() => expect(posts().length).toBeGreaterThan(0));
    const lastPost = posts()[posts().length - 1];
    expect(lastPost[0]).toMatch(/runs\/nexa-report$/);
    const body = JSON.parse(lastPost[1].body);
    expect(body.mission_type).toBe("LTSA_OPERATIONAL_REPORT_DRAFT");
    expect(body.start_date).toBe("2026-01-01");
    expect(body.end_date).toBe("2026-01-31");
  });
  it("renders NEXA operational report with evidence domains, provenance, and mandatory disclaimer", async () => {
    const nexaRun = {
      run_id: "run-nexa-test",
      mission_type: "LTSA_OPERATIONAL_REPORT_DRAFT",
      status: "AWAITING_REVIEW",
      requested_policy: "DAHONO_PRIMARY",
      actual_provider: "DAHONO",
      actual_model: "dahono/gpt-6-astra",
      fallback_used: false,
      elapsed_ms: 3500,
      draft_version: 1,
      period_start: "2026-01-01",
      period_end: "2026-01-31",
      evidence_sha256: "abc1234567890def1234567890abcdef1234567890abcdef1234567890abcdef",
      evidence_source_domains: ["condition_monitoring_reading", "pm_occurrence"],
      evidence_row_counts: { condition_monitoring_reading: 5, pm_occurrence: 2 },
      draft: {
        version: 1,
        content: "# LTSA OPERATIONAL REPORT\n## 1. Reporting Period\n## 2. Executive Summary\n## 3. Asset / Coverage Context\n## 4. Condition Monitoring Activity\n## 5. Preventive Maintenance Activity\n## 6. Installation Activity\n## 7. Mechanical Seal / Service Activity\n## 8. Data Gaps / Limitations\n## 9. Items Requiring Human Attention\n## 10. Evidence Summary",
      },
      review: null,
    };
    await loadRun(nexaRun);
    expect(screen.getByRole("heading", { name: "NEXA" })).toBeVisible();
    expect(screen.getByText(/2026-01-01 to 2026-01-31/)).toBeVisible();
    expect(screen.getByText(/condition_monitoring_reading, pm_occurrence/)).toBeVisible();
    expect(screen.getByText(/Approval confirms the report draft only. It does not publish, send, or modify LTSA operational data./)).toBeVisible();
    // Verify review buttons exist
    expect(screen.getByRole("button", { name: "Approve Draft" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
    // Zero external action buttons
    expect(screen.queryByRole("button", { name: /Send|Publish|WhatsApp|Email/i })).toBeNull();
  });
});
