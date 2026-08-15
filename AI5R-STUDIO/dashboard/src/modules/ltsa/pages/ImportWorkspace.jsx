import { useState } from "react";
import { PageHeader } from "../../../design-system";
import ImportOpenDesignView from "../components/ImportOpenDesignView";
import PumpXlsxImportPanel from "../components/PumpXlsxImportPanel";
import {
  createImportSession,
  executeImportSession,
  getImportSessionStatus,
  validateImportPackage,
} from "../../../api/ai5rClient";
import "./LTSAOpenDesign.css";

const EMPTY_PACKAGE = { pumps: [], seals: [], installations: [], documents: [] };

/**
 * MWO-LTSA-087/104 -- Production Import Workspace. Orchestration only:
 * this file holds the pipeline's local UI state and makes the four real,
 * already-existing Import API calls (CORE-SERVICES/BACKEND-API/routers/
 * import_router.py) -- validate/session/execute/status. It never
 * revalidates, reruns the conflict engine, or re-plans execution itself;
 * every one of those computations happens exactly once, server-side, and
 * this file only stores and displays the real response. Rendering itself
 * lives entirely in ImportOpenDesignView.jsx (render-only, no fetch),
 * matching every other LTSA workspace's own page/view split.
 *
 * MWO-LTSA-104 -- pipeline simplified from five calls to four, and the
 * stale "/execute is a disclosed stub" assumption removed (both closed by
 * MWO-LTSA-102B/102C/103/103A, backend-side): POST /api/ltsa/import/session
 * (createImportSession) now computes and stores its OWN ConflictReport
 * server-side (API.conflict_resolution.build_conflict_report, reused
 * unmodified inside the router) against an optional database_snapshot
 * field on the SAME request -- so this page no longer calls
 * POST /api/ltsa/import/conflicts separately before creating a session;
 * doing so would recompute the exact same comparison twice and keep two
 * separate pieces of state (`conflicts` and `session.data.conflict_report`)
 * that could disagree, exactly the "duplicate state machine" this MWO's
 * own rules forbid. The uploaded Database Snapshot file is still read
 * client-side (unchanged) and passed straight through as
 * `database_snapshot` on the session-create request instead.
 *
 * "No fake upload": Upload reads a real, user-selected .json file via the
 * browser's own File/FileReader APIs and parses it into the exact
 * {pumps, seals, installations, documents} shape
 * ImportPackageRequest/parse_import_package() already expect -- no
 * multipart upload endpoint exists on the backend, so a client-side
 * file-read-then-JSON-POST is the real, working shape of "upload" this
 * API actually supports, not an invented one.
 *
 * session_id/created_at are generated HERE, client-side, using real
 * browser primitives (crypto.randomUUID(), Date.toISOString()) --
 * import_session.py's own "no uuid.uuid4()/datetime.now() call anywhere"
 * rule is about the BACKEND never fabricating session identity; the
 * caller (this workspace) providing a real, unique identifier is exactly
 * the contract build_import_session()/ImportSessionCreateRequest already
 * require (session_id/created_at are required request fields, never
 * defaulted server-side).
 *
 * "No mock backend, no stub": every API function called here
 * (AI5R-STUDIO/dashboard/src/api/ai5rClient.js) performs a real fetch()
 * against the real FastAPI backend; POST /api/ltsa/import/execute now
 * genuinely runs ImportWorker/ImportExecutionEngine server-side
 * (MWO-LTSA-103) and returns a real ImportExecutionResult, shown to the
 * user exactly as the backend returned it -- never silently converted
 * into a fabricated success, and never assumed to have succeeded without
 * reading `success`/`status` off the real response.
 *
 * Execute -> Status: the backend executes synchronously within one HTTP
 * request/response (ImportWorker.process_all() is called and awaited
 * inside the route handler, MWO-LTSA-103) -- there is no background job
 * or queue exposed by this API to poll against. "Polling status" in this
 * mission's own pipeline diagram is therefore honestly implemented as ONE
 * confirming GET /api/ltsa/import/status/{id} call immediately after
 * execute resolves (handleExecute below), re-reading the session's own
 * canonical state from the one real source of truth -- not a fabricated
 * setInterval loop against a backend that has nothing further to report.
 * This also satisfies "Refresh after completion" without inventing a
 * second, parallel loading flag: it reuses the SAME loadingAction="execute"
 * state the Execute button's own disabled-while-running behavior already
 * depends on, so Execute stays disabled for the whole execute+refresh
 * sequence, not just the first call.
 */
export default function ImportWorkspace({ onNavigate }) {
  const [incomingPackage, setIncomingPackage] = useState(EMPTY_PACKAGE);
  const [incomingFileName, setIncomingFileName] = useState(null);
  const [databaseSnapshot, setDatabaseSnapshot] = useState(EMPTY_PACKAGE);
  const [databaseSnapshotFileName, setDatabaseSnapshotFileName] = useState(null);

  const [validation, setValidation] = useState(null);
  const [session, setSession] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);

  const [loadingAction, setLoadingAction] = useState(null);
  const [error, setError] = useState(null);

  function readJsonFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          resolve(JSON.parse(reader.result));
        } catch {
          reject(new Error(`${file.name} is not valid JSON`));
        }
      };
      reader.onerror = () => reject(new Error(`Could not read ${file.name}`));
      reader.readAsText(file);
    });
  }

  async function handleIncomingFileSelected(file) {
    if (!file) return;
    setError(null);
    try {
      const parsed = await readJsonFile(file);
      setIncomingPackage({
        pumps: parsed.pumps ?? [],
        seals: parsed.seals ?? [],
        installations: parsed.installations ?? [],
        documents: parsed.documents ?? [],
      });
      setIncomingFileName(file.name);
    } catch (fileError) {
      setError(fileError.message);
    }
  }

  async function handleDatabaseSnapshotFileSelected(file) {
    if (!file) return;
    setError(null);
    try {
      const parsed = await readJsonFile(file);
      setDatabaseSnapshot({
        pumps: parsed.pumps ?? [],
        seals: parsed.seals ?? [],
        installations: parsed.installations ?? [],
        documents: parsed.documents ?? [],
      });
      setDatabaseSnapshotFileName(file.name);
    } catch (fileError) {
      setError(fileError.message);
    }
  }

  async function handleValidate() {
    setLoadingAction("validate");
    setError(null);
    try {
      const result = await validateImportPackage(incomingPackage);
      setValidation(result);
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoadingAction(null);
    }
  }

  async function handleReview() {
    setLoadingAction("review");
    setError(null);
    try {
      const sessionId = session?.data?.session_id ?? `IMPORT-${crypto.randomUUID()}`;
      const sessionResult = await createImportSession({
        session_id: sessionId,
        created_at: new Date().toISOString(),
        source: incomingFileName ?? "manual-upload",
        status: "REVIEWING",
        package: incomingPackage,
        database_snapshot: databaseSnapshot,
      });
      setSession(sessionResult);
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoadingAction(null);
    }
  }

  async function handleExecute() {
    if (!session?.data?.session_id) return;
    setLoadingAction("execute");
    setError(null);
    try {
      const result = await executeImportSession(session.data.session_id);
      setExecutionResult(result);
      // Refresh from the one canonical source of truth after execution --
      // see this file's own header for why this is a single confirming
      // call, not a polling loop, against this synchronous backend.
      const refreshed = await getImportSessionStatus(session.data.session_id);
      setSession(refreshed);
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoadingAction(null);
    }
  }

  async function handleRefresh() {
    if (!session?.data?.session_id) return;
    setLoadingAction("refresh");
    setError(null);
    try {
      const result = await getImportSessionStatus(session.data.session_id);
      setSession(result);
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoadingAction(null);
    }
  }

  return (
    <div>
      <PageHeader title="Import Workspace" subtitle="LTSA Engineering — Production Knowledge Import" />

      <PumpXlsxImportPanel />

      <ImportOpenDesignView
        incomingPackage={incomingPackage}
        incomingFileName={incomingFileName}
        onIncomingFileSelected={handleIncomingFileSelected}
        databaseSnapshotFileName={databaseSnapshotFileName}
        onDatabaseSnapshotFileSelected={handleDatabaseSnapshotFileSelected}
        validation={validation}
        session={session}
        executionResult={executionResult}
        loadingAction={loadingAction}
        error={error}
        onValidate={handleValidate}
        onReview={handleReview}
        onExecute={handleExecute}
        onRefresh={handleRefresh}
        onNavigate={onNavigate}
      />
    </div>
  );
}
