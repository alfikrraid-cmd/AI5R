import { nextMonthFirstDay } from "./pmMapping";
import { buildPlannedActivitiesPayload } from "./pmActivityCatalog";

// AI5R-PHASE4E3 -- shared bulk-schedule row model, validation, and
// payload-building logic, kept in its OWN pure-function module (no React)
// so it's directly unit-testable and shareable between the bulk editor
// and (later) 4E.4's Excel import review surface, per this mission's own
// framing: "This table will later become the common review/editor
// surface for manual bulk entry AND Phase4E.4 Excel import."

// Section D: "Use only currently supported backend values" -- the exact
// same 4 values PMScheduleBulkRow's own backend validator enforces
// (CORE-SERVICES/BACKEND-API/models/requests.py, _SUPPORTED_FREQUENCIES).
export const SUPPORTED_FREQUENCIES = ["DAILY", "WEEKLY", "MONTHLY", "RUNTIME_BASED"];

// AI5R-PHASE4E2/4E3, Section B -- Trigger Type is derived, never a form
// field: DAILY/WEEKLY/MONTHLY -> CALENDAR, RUNTIME_BASED -> METER. Single
// source of truth for BOTH CreatePMScheduleModal (single create) and the
// bulk editor, so the two flows can never silently diverge.
export function deriveTriggerType(frequency) {
  return frequency === "RUNTIME_BASED" ? "METER" : "CALENDAR";
}

export function emptyBulkRow(id, overrides = {}) {
  return {
    id,
    selected: false,
    pumpTag: "",
    frequency: "MONTHLY",
    startDate: nextMonthFirstDay(),
    // AI5R-PHASE4E3, Section F: ALL new rows start with every planned
    // activity unchecked -- plannedMap is a plain {code: boolean} map,
    // the same shape CreatePMScheduleModal already uses for
    // PMActivityFamilyChecklist, so the compact-cell editor (Section N)
    // can reuse that exact component unmodified.
    plannedMap: {},
    technician: "",
    duration: "",
    notes: "",
    // AI5R-PHASE4E4, Section K -- optional, CLIENT-SIDE-ONLY source
    // metadata (never sent to the backend -- absent from
    // toBulkCreatePayloadRow's wire shape below). `source`/`sourceRow`
    // let the editor show "Excel row 17: ..." against a specific
    // imported row; `importErrors` carries parse-time problems that have
    // no valid slot in the structured fields above (e.g. an
    // unrecognized Planned Activities token) and are shown ALONGSIDE
    // live validateBulkRows() results, not instead of them. Every
    // manually-added row carries the same three fields at their
    // do-nothing defaults, so imported and manual rows share one model.
    source: null,
    sourceRow: null,
    importErrors: [],
    ...overrides,
  };
}

function isValidDuration(duration) {
  if (duration === "" || duration === null || duration === undefined) {
    return true; // optional field
  }
  const value = Number(duration);
  return Number.isFinite(value) && value >= 0;
}

// AI5R-PHASE4E3, Section G -- per-row classification. `canonicalPumpTags`
// is a Set of every real pump tag (from getPumps(), the same canonical
// master AssetSelector already uses -- Section D: never a second pump
// master). `existingActiveSchedules` is the already-loaded PM.jsx
// pmSchedules list (mapPMScheduleRecord shape: equipmentTag/frequency/
// status) -- used ONLY for the soft, non-blocking overlap WARNING
// (Section G: "Do not invent overlap semantics if backend has none" --
// this is a same-pump-and-frequency heuristic against data the UI
// already has, never a claimed backend uniqueness rule).
export function validateBulkRows(rows, { canonicalPumpTags = new Set(), existingActiveSchedules = [] } = {}) {
  const results = {};
  const seenExactKey = new Map(); // pumpTag::frequency::startDate -> row.id (ERROR: exact duplicate)
  const seenPumpFrequency = new Map(); // pumpTag::frequency -> row.id[] (WARNING: same pump+frequency, different date)

  for (const row of rows) {
    const errors = [];
    const warnings = [];

    if (!row.pumpTag) {
      errors.push("Pump is required.");
    } else if (canonicalPumpTags.size > 0 && !canonicalPumpTags.has(row.pumpTag)) {
      errors.push(`Unknown pump: ${row.pumpTag} (not in the canonical pump master).`);
    }

    if (!row.frequency) {
      errors.push("Frequency is required.");
    } else if (!SUPPORTED_FREQUENCIES.includes(row.frequency)) {
      // AI5R-PHASE4E4, Section P -- distinguishes "nothing was given" from
      // "something was given but isn't a recognized value" (e.g. an
      // Excel cell that fell through frequency-alias mapping unchanged),
      // matching the mission's own example: `Frequency "3 Monthly" is
      // unsupported.`
      errors.push(`Frequency "${row.frequency}" is unsupported.`);
    }

    if (!row.startDate) {
      errors.push("Start Date is required.");
    } else if (!/^\d{4}-\d{2}-\d{2}$/.test(row.startDate)) {
      // AI5R-PHASE4E4 -- the UI's own <input type="date"> always produces
      // ISO YYYY-MM-DD, so this only ever fires for an imported row whose
      // date could not be resolved to that canonical form (Section H).
      errors.push(`Start Date "${row.startDate}" is invalid.`);
    }

    if (!isValidDuration(row.duration)) {
      errors.push("Duration must be zero or more hours.");
    }

    // Structurally unreachable via the UI (the canonical catalog has no
    // RESERVOIR_DE/RESERVOIR_NDE code at all), kept as a defensive
    // classification per Section G's own explicit "Reservoir DE/NDE"
    // ERROR bullet, in case a row's plannedMap is ever populated by a
    // future non-UI caller (e.g. 4E.4's Excel import).
    for (const [code, checked] of Object.entries(row.plannedMap || {})) {
      if (checked && (code === "RESERVOIR_DE" || code === "RESERVOIR_NDE")) {
        errors.push("Reservoir does not have DE/NDE variants.");
      }
    }

    if (row.pumpTag && row.frequency && row.startDate) {
      const exactKey = `${row.pumpTag}::${row.frequency}::${row.startDate}`;
      if (seenExactKey.has(exactKey)) {
        errors.push("Duplicate of another row: same pump + frequency + start date in this batch.");
      } else {
        seenExactKey.set(exactKey, row.id);
      }

      const pumpFrequencyKey = `${row.pumpTag}::${row.frequency}`;
      if (seenPumpFrequency.has(pumpFrequencyKey)) {
        warnings.push("Another row in this batch targets the same pump + frequency with a different start date.");
      }
      seenPumpFrequency.set(pumpFrequencyKey, row.id);

      const overlapsActive = existingActiveSchedules.some(
        (schedule) =>
          schedule.equipmentTag === row.pumpTag &&
          schedule.frequency === row.frequency &&
          schedule.status === "ACTIVE"
      );
      if (overlapsActive) {
        warnings.push("An ACTIVE schedule already exists for this pump and frequency.");
      }
    }

    const level = errors.length > 0 ? "ERROR" : warnings.length > 0 ? "WARNING" : "READY";
    results[row.id] = { errors, warnings, level };
  }

  const values = Object.values(results);
  const summary = {
    rows: rows.length,
    ready: values.filter((r) => r.level === "READY").length,
    warnings: values.filter((r) => r.level === "WARNING").length,
    errors: values.filter((r) => r.level === "ERROR").length,
  };

  return { results, summary };
}

// AI5R-PHASE4E3, Section I -- converts one internal row into the exact
// wire shape POST /api/ltsa/pm-schedules/bulk expects. `client_row_id`
// round-trips through the response so a create result (or a server-side
// validation error) can be correlated back to this exact row.
export function toBulkCreatePayloadRow(row) {
  const plannedActivities = buildPlannedActivitiesPayload(row.plannedMap || {});
  return {
    client_row_id: row.id,
    asset_code: row.pumpTag,
    procedure: row.notes || null,
    frequency: row.frequency,
    trigger_type: deriveTriggerType(row.frequency),
    effective_date: row.startDate || null,
    next_due: row.startDate || null,
    assigned_to: row.technician || null,
    estimated_duration_hours: row.duration === "" ? null : Number(row.duration),
    planned_activities: plannedActivities.length > 0 ? plannedActivities : null,
  };
}

export function toBulkCreatePayload(rows) {
  return { rows: rows.map(toBulkCreatePayloadRow) };
}

export function countPlannedActivities(plannedMap) {
  return Object.values(plannedMap || {}).filter(Boolean).length;
}
