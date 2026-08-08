const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";


export async function getSystemStatus(){

    try{

        const response = await fetch(
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

        const response = await fetch(
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
    const response = await fetch(`${API_URL}/api/ltsa/equipment`);

    if (!response.ok) {
        throw new Error("Equipment API unavailable");
    }

    return normalizeEquipmentList(await response.json());
}


export async function getEquipment(equipmentId) {
    const response = await fetch(
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
    const response = await fetch(
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
    const response = await fetch(
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
    const response = await fetch(
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
    const response = await fetch(`${API_URL}/api/ltsa/workorders`);

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
    const response = await fetch(
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
    const response = await fetch(
        `${API_URL}/api/ltsa/workorders/${encodeURIComponent(workOrderId)}/asset`
    );

    if (!response.ok) {
        throw new Error("Work order asset API unavailable");
    }

    return await response.json();
}

export async function getPumps() {
    const response = await fetch(`${API_URL}/api/ltsa/pumps`);

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
    const response = await fetch(`${API_URL}/api/ltsa/pumps/${encodeURIComponent(tagNumber)}`);

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
    const response = await fetch(
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
    const response = await fetch(
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
    const response = await fetch(`${API_URL}/api/ltsa/pm-schedules`);

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
    const response = await fetch(`${API_URL}/api/ltsa/cm-reports`);

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
    const response = await fetch(`${API_URL}/api/ltsa/pm-occurrences`);

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
    const response = await fetch(`${API_URL}/api/ltsa/condition-monitoring-readings`);

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
    const response = await fetch(`${API_URL}/api/ltsa/condition-monitoring-schedules`);

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
    const response = await fetch(`${API_URL}/api/ltsa/maintenance-history`);

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
    const response = await fetch(
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
    const response = await fetch(
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
    const response = await fetch(
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
    const response = await fetch(`${API_URL}/api/ltsa/workorders`, {
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
    const response = await fetch(
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
    const response = await fetch(`${API_URL}/api/ltsa/engineering-ai`, {
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
    const response = await fetch(
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

// Fleet Reliability API (MWO-LTSA-037C, consumed by MWO-LTSA-037D's Fleet
// Dashboard). One endpoint, {success, data} shape -- same convention as
// getPumpKnowledge.
export async function getFleetReliability() {
    const response = await fetch(`${API_URL}/api/ltsa/fleet/reliability`);

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
    const response = await fetch(`${API_URL}/api/ltsa/fleet/powerbi`);

    if (!response.ok) {
        throw new Error("Fleet Power BI API unavailable");
    }

    const payload = await response.json();

    if (payload?.success === false) {
        throw new Error(payload?.message || "Fleet Power BI API returned a failure");
    }

    return payload;
}
