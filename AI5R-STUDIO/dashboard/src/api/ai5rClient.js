const API_URL = import.meta.env.VITE_API_URL || "http://localhost:18000";

// MWO-LTSA-AUTH-002 -- the one canonical session store + authenticated-
// request mechanism every LTSA API call goes through (Authorization:
// Bearer <token>, centrally, never duplicated per call site). authClient.js
// (POST /api/auth/login, GET /api/auth/me) reads/writes the SAME session
// record via these exports rather than keeping a second copy of the
// storage key, so there is exactly one place a token can live.
const SESSION_KEY = "ai5r.ltsa.session";

export function getStoredSession() {
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function storeSession(session) {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearStoredSession() {
  window.localStorage.removeItem(SESSION_KEY);
}

// AuthContext registers itself here once (see AuthContext.jsx) so that a
// 401 from ANY protected LTSA call -- not just /api/auth/me -- clears the
// session and returns to LoginView (Rule 6), without ai5rClient importing
// React state directly.
let _unauthorizedHandler = null;
export function onUnauthorized(handler) {
  _unauthorizedHandler = handler;
}

// Every LTSA/platform fetch in this file goes through here instead of the
// global fetch directly, so Bearer-token attachment and 401 handling are
// implemented exactly once, not duplicated across every workspace's own
// API function (per this MWO's Rule 5).
async function apiFetch(input, options = {}) {
  const session = getStoredSession();
  const headers = { ...(options.headers || {}) };
  if (session?.token) {
    headers.Authorization = `Bearer ${session.token}`;
  }

  const response = await fetch(input, { ...options, headers });

  if (response.status === 401) {
    clearStoredSession();
    _unauthorizedHandler?.();
  }

  return response;
}


export async function getSystemStatus(){

    try{

        const response = await apiFetch(
            `${API_URL}/health`
        );


        if(!response.ok){

            throw new Error(
                "API unavailable"
            );

        }


        return await response.json();


    }catch(error){

        return {

            status:"OFFLINE",

            system:"AI5R",

            service:"COMMAND_CENTER"

        };

    }

}



export async function getDashboardData(){

    try{

        const response = await apiFetch(
            `${API_URL}/dashboard`
        );


        if(!response.ok){

            throw new Error(
                "Dashboard API unavailable"
            );

        }


        return await response.json();


    }catch(error){

        return {

            system_status:"OFFLINE",

            brain_status:"UNKNOWN",

            agents:0,

            memories:0,

            governance:"UNKNOWN"

        };

    }

}


function normalizeEquipmentList(payload) {
    if (Array.isArray(payload)) {
        return payload;
    }

    if (Array.isArray(payload?.items)) {
        return payload.items;
    }

    if (Array.isArray(payload?.equipment)) {
        return payload.equipment;
    }

    throw new Error("Equipment API returned an invalid list");
}


export async function getEquipmentList() {
    const response = await apiFetch(`${API_URL}/api/ltsa/equipment`);

    if (!response.ok) {
        throw new Error("Equipment API unavailable");
    }

    return normalizeEquipmentList(await response.json());
}


export async function getEquipment(equipmentId) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/equipment/${encodeURIComponent(equipmentId)}`
    );

    if (!response.ok) {
        throw new Error("Equipment detail API unavailable");
    }

    const payload = await response.json();
    const equipment = payload?.equipment ?? payload;

    if (!equipment || typeof equipment !== "object" || Array.isArray(equipment)) {
        throw new Error("Equipment API returned an invalid detail");
    }

    return equipment;
}

export async function getEquipmentInspections(equipmentId) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/equipment/${encodeURIComponent(equipmentId)}/inspections`
    );

    if (!response.ok) {
        throw new Error("Inspection history API unavailable");
    }

    const payload = await response.json();

    if (Array.isArray(payload)) {
        return payload;
    }

    if (Array.isArray(payload?.items)) {
        return payload.items;
    }

    if (Array.isArray(payload?.inspections)) {
        return payload.inspections;
    }

    throw new Error("Inspection history API returned an invalid list");
}

export async function getInspectionFindings(inspectionId) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/inspections/${encodeURIComponent(inspectionId)}/findings`
    );

    if (!response.ok) {
        throw new Error("Inspection findings API unavailable");
    }

    const payload = await response.json();

    if (Array.isArray(payload)) {
        return payload;
    }

    if (Array.isArray(payload?.items)) {
        return payload.items;
    }

    if (Array.isArray(payload?.findings)) {
        return payload.findings;
    }

    throw new Error("Inspection findings API returned an invalid list");
}
export async function getFindingWorkOrders(findingId) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/findings/${encodeURIComponent(findingId)}/workorders`
    );
    if (!response.ok) throw new Error("Finding work orders API unavailable");
    const payload = await response.json();
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.items)) return payload.items;
    if (Array.isArray(payload?.workorders)) return payload.workorders;
    if (Array.isArray(payload?.work_orders)) return payload.work_orders;
    throw new Error("Finding work orders API returned an invalid list");
}

export async function getWorkOrders() {
    const response = await apiFetch(`${API_URL}/api/ltsa/workorders`);

    if (!response.ok) {
        throw new Error("Work orders API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Work orders API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("Work orders API returned an invalid list");
}

export async function getWorkOrder(workOrderId) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/workorders/${encodeURIComponent(workOrderId)}`
    );

    if (!response.ok) {
        throw new Error("Work order detail API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Work order detail API returned a failure");
    }

    const workOrder = payload?.data ?? payload;

    if (!workOrder || typeof workOrder !== "object" || Array.isArray(workOrder)) {
        throw new Error("Work order API returned an invalid detail");
    }

    return workOrder;
}

// Returns the raw {success, message, asset_code, asset_type, area} payload
// unchanged -- success: false (unsupported asset_type, unknown asset) is a
// legitimate, expected outcome per WO-BE-003, not treated as an error the
// caller must catch. Callers read `.area`, which is null when unresolved.
export async function getWorkOrderAsset(workOrderId) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/workorders/${encodeURIComponent(workOrderId)}/asset`
    );

    if (!response.ok) {
        throw new Error("Work order asset API unavailable");
    }

    return await response.json();
}

export async function getPumps() {
    const response = await apiFetch(`${API_URL}/api/ltsa/pumps`);

    if (!response.ok) {
        throw new Error("Pumps API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Pumps API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("Pumps API returned an invalid list");
}

export async function getPump(tagNumber) {
    const response = await apiFetch(`${API_URL}/api/ltsa/pumps/${encodeURIComponent(tagNumber)}`);

    if (!response.ok) {
        throw new Error("Pump detail API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Pump detail API returned a failure");
    }

    const pump = payload?.data ?? payload;

    if (!pump || typeof pump !== "object" || Array.isArray(pump)) {
        throw new Error("Pump API returned an invalid detail");
    }

    return pump;
}

// { success, tag_number, openWO, data } -- see WO-PUMP-003. success: false
// here reflects a real upstream failure (unlike getWorkOrderAsset's
// success: false, which is a legitimate "unresolved" outcome), so it is
// treated as an error.
export async function getPumpOpenWorkOrders(tagNumber) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/pumps/${encodeURIComponent(tagNumber)}/workorders`
    );

    if (!response.ok) {
        throw new Error("Pump open work orders API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Pump open work orders API returned a failure");
    }

    return payload;
}

// { success, tag_number, last_pm } -- see WO-PUMP-004. success: false here
// reflects a real upstream failure (same convention as getPumpOpenWorkOrders),
// so it is treated as an error.
export async function getPumpLastPM(tagNumber) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/pumps/${encodeURIComponent(tagNumber)}/last-pm`
    );

    if (!response.ok) {
        throw new Error("Pump last PM API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Pump last PM API returned a failure");
    }

    return payload;
}

export async function getPMSchedules() {
    const response = await apiFetch(`${API_URL}/api/ltsa/pm-schedules`);

    if (!response.ok) {
        throw new Error("PM schedules API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "PM schedules API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("PM schedules API returned an invalid list");
}

export async function getCMReports() {
    const response = await apiFetch(`${API_URL}/api/ltsa/cm-reports`);

    if (!response.ok) {
        throw new Error("CM reports API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "CM reports API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("CM reports API returned an invalid list");
}

// WO-ASSET360-001 (per ADR-ASSET360-001): required by the future Asset
// 360 History composition -- neither function is consumed by any page
// yet (APP-ASSET360-001, not started). No dedicated test file exists for
// ai5rClient.js's other list functions either (getPMSchedules,
// getCMReports, etc.), so none is added for these two.

export async function getPMOccurrences() {
    const response = await apiFetch(`${API_URL}/api/ltsa/pm-occurrences`);

    if (!response.ok) {
        throw new Error("PM occurrences API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "PM occurrences API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("PM occurrences API returned an invalid list");
}

export async function getConditionMonitoringReadings() {
    const response = await apiFetch(`${API_URL}/api/ltsa/condition-monitoring-readings`);

    if (!response.ok) {
        throw new Error("Condition Monitoring readings API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Condition Monitoring readings API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("Condition Monitoring readings API returned an invalid list");
}

// APP-ASSET360-001: fills a second gap found only at implementation time --
// GET /api/ltsa/condition-monitoring-schedules has existed since
// WO-CMON-002, but no client function ever called it. Required for the
// Asset 360 Active Plans zone.
export async function getConditionMonitoringSchedules() {
    const response = await apiFetch(`${API_URL}/api/ltsa/condition-monitoring-schedules`);

    if (!response.ok) {
        throw new Error("Condition Monitoring schedules API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Condition Monitoring schedules API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("Condition Monitoring schedules API returned an invalid list");
}

// APP-ASSET360-001 (per ADR-ASSET360-001): getMaintenanceHistory() fills a
// gap found only at implementation time -- GET /api/ltsa/maintenance-history
// has existed since WO-MH-002, but no client function ever called it.
// Required for the Asset 360 History stream's MH event source.
export async function getMaintenanceHistory() {
    const response = await apiFetch(`${API_URL}/api/ltsa/maintenance-history`);

    if (!response.ok) {
        throw new Error("Maintenance history API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Maintenance history API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("Maintenance history API returned an invalid list");
}

// { success, tag_number, last_cm } -- see WO-ASSET360-001. success: false
// here reflects a real upstream failure, so it is treated as an error, the
// same convention as getPumpLastPM.
export async function getPumpLastCM(tagNumber) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/pumps/${encodeURIComponent(tagNumber)}/last-cm`
    );

    if (!response.ok) {
        throw new Error("Pump last CM API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Pump last CM API returned a failure");
    }

    return payload;
}

// { success, tag_number, flagged, window_days, latest_flagged_reading } --
// see WO-ASSET360-001. success: false here reflects a real upstream
// failure, so it is treated as an error, the same convention as
// getPumpLastPM/getPumpLastCM.
export async function getPumpConditionMonitoringFlag(tagNumber) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/pumps/${encodeURIComponent(tagNumber)}/condition-monitoring-flag`
    );

    if (!response.ok) {
        throw new Error("Pump Condition Monitoring flag API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Pump Condition Monitoring flag API returned a failure");
    }

    return payload;
}

// { success, tag_number, spare_parts } -- see MWO-INV-CTX-001. success: false
// here reflects a real upstream failure, same convention as getPumpLastPM/
// getPumpLastCM/getPumpConditionMonitoringFlag.
export async function getPumpSpareParts(tagNumber) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/pumps/${encodeURIComponent(tagNumber)}/spare-parts`
    );

    if (!response.ok) {
        throw new Error("Pump spare parts API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Pump spare parts API returned a failure");
    }

    return payload;
}

export async function createWorkOrder(payload) {
    const response = await apiFetch(`${API_URL}/api/ltsa/workorders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error("Work order create API unavailable");
    }

    const result = await response.json();

    if (result?.success === false) {
        throw new Error(result?.message || "Work order create API returned a failure");
    }

    return result?.data ?? result;
}

export async function getWorkOrderTimeline(workOrderId) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/workorders/${encodeURIComponent(workOrderId)}/timeline`
    );

    if (!response.ok) {
        throw new Error("Work order timeline API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Work order timeline API returned a failure");
    }

    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload)) return payload;

    throw new Error("Work order timeline API returned an invalid list");
}

// Engineering AI: the single canonical entry point every LTSA workspace
// SHALL call for AI execution (per the Engineering AI platform's own
// architecture). This function performs HTTP transport only -- it builds
// no prompt, no context, no AI client, and never talks to a provider or
// Router directly. The backend (POST /api/ltsa/engineering-ai) already
// validates and serializes EngineeringAIRequest/EngineeringAIResponse; on
// failure it returns a FastAPI-style {"detail": "..."} body, read here the
// same way every other error path in this file already surfaces a message.
export async function postEngineeringAI(request) {
    const response = await apiFetch(`${API_URL}/api/ltsa/engineering-ai`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
    });

    const payload = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Engineering AI API unavailable");
    }

    if (payload?.success === false) {
        throw new Error(payload?.message || "Engineering AI API returned a failure");
    }

    return payload;
}

// Knowledge API (MWO-LTSA-031D backend, consumed by MWO-LTSA-032A's
// Knowledge Workspace). One endpoint, mirrors getPumpSpareParts/
// getPumpConditionMonitoringFlag's own {success, tag_number, data} shape.
export async function getPumpKnowledge(tagNumber) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/pumps/${encodeURIComponent(tagNumber)}/knowledge`
    );

    if (!response.ok) {
        throw new Error("Pump knowledge API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Pump knowledge API returned a failure");
    }

    return payload;
}

// Pump Lifecycle API (MWO-LTSA-064A backend, consumed by MWO-LTSA-065's
// Pump Workspace Lifecycle Integration). One endpoint, {success,
// tag_number, data} shape -- same convention as getPumpKnowledge/
// getPumpSpareParts. This is the ONE fetch Pump Workspace's detail view
// uses for current state, timeline, related engineering, and analytics --
// see pumpLifecycleMapping.js for the field mapping.
export async function getPumpLifecycle(tagNumber) {
    const response = await apiFetch(
        `${API_URL}/api/ltsa/pumps/${encodeURIComponent(tagNumber)}/lifecycle`
    );

    if (!response.ok) {
        throw new Error("Pump lifecycle API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Pump lifecycle API returned a failure");
    }

    return payload;
}

// Fleet Reliability API (MWO-LTSA-037C, consumed by MWO-LTSA-037D's Fleet
// Dashboard). One endpoint, {success, data} shape -- same convention as
// getPumpKnowledge.
export async function getFleetReliability() {
    const response = await apiFetch(`${API_URL}/api/ltsa/fleet/reliability`);

    if (!response.ok) {
        throw new Error("Fleet reliability API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Fleet reliability API returned a failure");
    }

    return payload;
}

// Power BI API (MWO-LTSA-038A, consumed by MWO-LTSA-038B's Power BI
// Dashboard foundation). One endpoint, {success, data} shape -- same
// convention as getPumpKnowledge/getFleetReliability.
export async function getFleetPowerBI() {
    const response = await apiFetch(`${API_URL}/api/ltsa/fleet/powerbi`);

    if (!response.ok) {
        throw new Error("Fleet Power BI API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Fleet Power BI API returned a failure");
    }

    return payload;
}

// Mechanical Seal Workspace API (MWO-LTSA-041, per MWO-LTSA-040's
// archaeology). Same list-unwrapping convention as getPumps().
export async function getSeals() {
    const response = await apiFetch(`${API_URL}/api/ltsa/seals`);

    if (!response.ok) {
        throw new Error("Seals API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Seals API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("Seals API returned an invalid list");
}

// Document Workspace API (MWO-LTSA-062, Document & Drawing
// Productionization). Reuses the real seal_engineering_document data
// source Drawing already reads via getPumpKnowledge().data.drawings, but
// unfiltered (every document_type, not just DRAWING) -- Document.jsx
// filters/groups client-side. Same list-unwrapping convention as
// getSeals()/getPumps(). Drawing Workspace also calls this same function
// to resolve its own Document/Seal relationships -- not a second fetcher.
export async function getDocuments() {
    const response = await apiFetch(`${API_URL}/api/ltsa/documents`);

    if (!response.ok) {
        throw new Error("Documents API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Documents API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("Documents API returned an invalid list");
}

// Installation Report API (MWO-LTSA-060, production persistence path for
// the Installation Workspace created by MWO-LTSA-056). Same
// list-unwrapping convention as getSeals()/getPumps().
export async function getInstallations() {
    const response = await apiFetch(`${API_URL}/api/ltsa/installations`);

    if (!response.ok) {
        throw new Error("Installations API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Installations API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("Installations API returned an invalid list");
}

export async function getSealStock() {
    const response = await apiFetch(`${API_URL}/api/ltsa/seal-stock`);

    if (!response.ok) {
        throw new Error("Seal Stock API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Seal Stock API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("Seal Stock API returned an invalid list");
}

export async function getSealCompatibility() {
    const response = await apiFetch(`${API_URL}/api/ltsa/seal-compatibility`);

    if (!response.ok) {
        throw new Error("Seal Compatibility API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Seal Compatibility API returned a failure");
    }

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.items)) return payload.items;

    throw new Error("Seal Compatibility API returned an invalid list");
}

// Import API (MWO-LTSA-076/077/079/081/085/102B/102C/103/103A,
// CORE-SERVICES/BACKEND-API/routers/import_router.py) -- five real,
// already-existing endpoints (checkImportConflicts kept for direct
// /conflicts callers even though ImportWorkspace.jsx no longer calls it
// itself as of MWO-LTSA-104 -- POST /session now computes and stores its
// own ConflictReport server-side). Every function below returns the
// backend's own {success, data, message?} envelope UNTHROWN on
// success:false (unlike postEngineeringAI's own throw-on-failure
// convention) -- a validation/conflict/execute response with success:false
// is a real, informative outcome the Import Workspace must display (e.g.
// "N validation errors", or a real REJECTED_CONFLICTS/FAILED_ROLLED_BACK
// execution outcome), never an exceptional crash. Only a genuine
// HTTP-level failure or unparseable body throws.
async function _postImportApi(path, body) {
    const response = await apiFetch(`${API_URL}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    const payload = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || `Import API ${path} unavailable`);
    }

    return payload;
}

export async function validateImportPackage(importPackage) {
    return _postImportApi("/api/ltsa/import/validate", importPackage);
}

export async function checkImportConflicts(databaseSnapshot, incomingPackage) {
    return _postImportApi("/api/ltsa/import/conflicts", {
        database_snapshot: databaseSnapshot,
        incoming_package: incomingPackage,
    });
}

export async function createImportSession(sessionRequest) {
    return _postImportApi("/api/ltsa/import/session", sessionRequest);
}

export async function executeImportSession(sessionId) {
    return _postImportApi("/api/ltsa/import/execute", { session_id: sessionId });
}

export async function getImportSessionStatus(sessionId) {
    const response = await apiFetch(`${API_URL}/api/ltsa/import/status/${encodeURIComponent(sessionId)}`);
    const payload = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Import Status API unavailable");
    }

    return payload;
}

// Pump Master XLSX dry-run (MWO-LTSA-DATA-IMPORT-UI-001B,
// CORE-SERVICES/BACKEND-API/routers/import_router.py POST
// /api/ltsa/import/pump-xlsx/dry-run) -- real multipart upload of a real
// .xlsx File the browser gives us, no client-side parsing. Same
// success:false-is-not-an-exception convention as _postImportApi above: a
// rejected extension or an unreadable workbook is a real, informative
// {success:false, message} response to render, not a thrown error --
// only a genuine HTTP/network failure throws.
export async function dryRunPumpXlsx(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await apiFetch(`${API_URL}/api/ltsa/import/pump-xlsx/dry-run`, {
        method: "POST",
        body: formData,
    });

    const payload = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Pump XLSX dry-run API unavailable");
    }

    return payload;
}

// MWO-LTSA-AUTH-003A-FINAL -- Admin Users API. Every call requires
// admin.users (enforced server-side, routers/admin_users.py); a 403 here
// always means the real backend denied it (delegation scope), never a
// frontend-only gate -- errors surface `detail` (FastAPI's own field,
// e.g. "TAP_ADMIN is not authorized to manage SUPERUSER accounts") the
// same way dryRunPumpXlsx() already does above.
async function _adminUsersRequest(input, options) {
    const response = await apiFetch(input, options);
    const payload = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Admin Users API unavailable");
    }

    return payload;
}

export async function getAdminUsers() {
    const payload = await _adminUsersRequest(`${API_URL}/api/admin/users`);
    return Array.isArray(payload?.users) ? payload.users : [];
}

export async function createAdminUser({ email, password, organizationId, role }) {
    return _adminUsersRequest(`${API_URL}/api/admin/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, organization_id: organizationId, role }),
    });
}

export async function updateAdminUserStatus(userId, status) {
    return _adminUsersRequest(`${API_URL}/api/admin/users/${encodeURIComponent(userId)}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
    });
}

export async function updateAdminUserRole(userId, organizationId, role) {
    return _adminUsersRequest(`${API_URL}/api/admin/users/${encodeURIComponent(userId)}/role`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ organization_id: organizationId, role }),
    });
}

export async function resetAdminUserPassword(userId, newPassword) {
    return _adminUsersRequest(`${API_URL}/api/admin/users/${encodeURIComponent(userId)}/password-reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_password: newPassword }),
    });
}

// MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- manual completion of KIMAP
// Pertamina / GPN John Crane (PATCH /api/ltsa/seals/{seal_code},
// master.edit). Same verbatim-backend-error-surfacing discipline as
// _adminUsersRequest above (a 403/404 detail string is thrown as-is, not
// swallowed into a generic message) -- reused directly rather than a
// second near-identical helper.
export async function updateSealIdentifiers(sealCode, { kimapPertamina, gpnJohnCrane }) {
    return _adminUsersRequest(`${API_URL}/api/ltsa/seals/${encodeURIComponent(sealCode)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kimap_pertamina: kimapPertamina, gpn_john_crane: gpnJohnCrane }),
    });
}

// MWO-LTSA-PM-CM-INTAKE-001 -- real PM Occurrence / Condition Monitoring
// Reading draft-create/update/submit/review persistence, plus evidence
// attachments. Reuses _adminUsersRequest's verbatim-backend-error
// discipline (a 403/404/409 detail string is surfaced as-is, never
// swallowed) -- it is generic over URL/options despite its name, not
// admin-users-specific.

export async function createPMOccurrence({ pmScheduleCode, assetCode, assetType, occurrenceDate, activities, remarks }) {
    return _adminUsersRequest(`${API_URL}/api/ltsa/pm-occurrences`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            pm_schedule_code: pmScheduleCode, asset_code: assetCode, asset_type: assetType,
            occurrence_date: occurrenceDate, activities, remarks,
        }),
    });
}

export async function updatePMOccurrenceDraft(code, { occurrenceDate, activities, finding, preliminaryRecommendation, remarks }) {
    return _adminUsersRequest(`${API_URL}/api/ltsa/pm-occurrences/${encodeURIComponent(code)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            occurrence_date: occurrenceDate, activities, finding,
            preliminary_recommendation: preliminaryRecommendation, remarks,
        }),
    });
}

export async function submitPMOccurrence(code) {
    return _adminUsersRequest(`${API_URL}/api/ltsa/pm-occurrences/${encodeURIComponent(code)}/submit`, {
        method: "POST",
    });
}

export async function adminReviewPMOccurrence(code, returnReason) {
    return _adminUsersRequest(`${API_URL}/api/ltsa/pm-occurrences/${encodeURIComponent(code)}/admin-review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ return_reason: returnReason }),
    });
}

export async function technicalReviewPMOccurrence(code, { action, comment, recommendation }) {
    return _adminUsersRequest(`${API_URL}/api/ltsa/pm-occurrences/${encodeURIComponent(code)}/technical-review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, comment, recommendation }),
    });
}

export async function createConditionMonitoringReading({
    conditionMonitoringScheduleCode, assetCode, assetType, readingDate, measurements,
}) {
    return _adminUsersRequest(`${API_URL}/api/ltsa/condition-monitoring-readings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            condition_monitoring_schedule_code: conditionMonitoringScheduleCode, asset_code: assetCode,
            asset_type: assetType, reading_date: readingDate, measurements,
        }),
    });
}

export async function updateConditionMonitoringReadingDraft(code, { readingDate, measurements, finding }) {
    return _adminUsersRequest(`${API_URL}/api/ltsa/condition-monitoring-readings/${encodeURIComponent(code)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reading_date: readingDate, measurements, finding }),
    });
}

export async function submitConditionMonitoringReading(code) {
    return _adminUsersRequest(`${API_URL}/api/ltsa/condition-monitoring-readings/${encodeURIComponent(code)}/submit`, {
        method: "POST",
    });
}

export async function adminReviewConditionMonitoringReading(code, returnReason) {
    return _adminUsersRequest(
        `${API_URL}/api/ltsa/condition-monitoring-readings/${encodeURIComponent(code)}/admin-review`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ return_reason: returnReason }),
        }
    );
}

export async function technicalReviewConditionMonitoringReading(code, { action, comment, recommendation }) {
    return _adminUsersRequest(
        `${API_URL}/api/ltsa/condition-monitoring-readings/${encodeURIComponent(code)}/technical-review`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action, comment, recommendation }),
        }
    );
}

// Evidence upload is multipart, not JSON -- FormData, no Content-Type
// header (the browser sets the multipart boundary itself).
export async function uploadPMCMEvidence({ recordType, recordCode, category, file }) {
    const formData = new FormData();
    formData.append("record_type", recordType);
    formData.append("record_code", recordCode);
    if (category) formData.append("category", category);
    formData.append("file", file);
    return _adminUsersRequest(`${API_URL}/api/ltsa/pm-cm-evidence`, { method: "POST", body: formData });
}

export async function getPMCMEvidence(recordType, recordCode) {
    const payload = await _adminUsersRequest(
        `${API_URL}/api/ltsa/pm-cm-evidence?record_type=${encodeURIComponent(recordType)}&record_code=${encodeURIComponent(recordCode)}`
    );
    return Array.isArray(payload?.data) ? payload.data : [];
}

export function pmCMEvidenceDownloadUrl(evidenceId) {
    return `${API_URL}/api/ltsa/pm-cm-evidence/${encodeURIComponent(evidenceId)}/download`;
}
