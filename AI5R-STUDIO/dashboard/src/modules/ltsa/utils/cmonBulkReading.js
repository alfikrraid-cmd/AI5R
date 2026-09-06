import { emptyMeasurementFormValues, buildMeasurementsPayload } from "./conditionMonitoringMeasurementFields";

// MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001 -- shared bulk-reading row model,
// validation, and payload-building logic, mirroring pmBulkSchedule.js's
// own shape (pure functions, no React, directly unit-testable) but for
// the CMON domain, which has genuinely different rules: no frequency/
// trigger-type/planned-activities at all, and every measurement stays
// DE/NDE-only (never a General variant) with null-safe blank handling
// reused verbatim from conditionMonitoringMeasurementFields.js -- no
// second measurement catalog.

export function emptyBulkCmonRow(id, overrides = {}) {
  return {
    id,
    selected: false,
    pumpTag: "",
    readingDate: "",
    finding: "",
    // Every new row starts with every measurement blank/not-recorded --
    // the same emptyMeasurementFormValues() the single Add Reading form
    // uses, reused unmodified so bulk rows and the single form can never
    // diverge on what "blank" means.
    measurements: emptyMeasurementFormValues(),
    // MWO-LTSA-CMON-EXCEL-IMPORT-001, Section K -- optional, CLIENT-SIDE-
    // ONLY source metadata (never sent to the backend --
    // toBulkAdHocPayloadRow below never reads these). source/sourceRow
    // let the editor show "Excel row 17: ..." against a specific
    // imported row; importErrors carries parse-time problems that have
    // no valid slot in the structured fields above (invalid numeric
    // text, an unrecognized leak token). Every manually-added row
    // carries the same three fields at their do-nothing defaults, so
    // imported and manual rows share one model.
    source: null,
    sourceRow: null,
    importErrors: [],
    ...overrides,
  };
}

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

// `canonicalPumpTags` is a Set of every real pump tag (getPumps(), the
// same canonical master AssetSelector already uses). No duplicate-pump
// rule is enforced here: multiple readings for the same pump at
// different times in one batch are a legitimate, real operational
// pattern (reading_date is a TIMESTAMP, not a once-per-day key) and no
// existing backend uniqueness constraint says otherwise -- inventing
// one here would contradict "do not invent business rules the backend
// doesn't already have."
export function validateBulkCmonRows(rows, { canonicalPumpTags = new Set() } = {}) {
  const results = {};

  for (const row of rows) {
    const errors = [];

    if (!row.pumpTag) {
      errors.push("Pump is required.");
    } else if (canonicalPumpTags.size > 0 && !canonicalPumpTags.has(row.pumpTag)) {
      errors.push(`Unknown pump: ${row.pumpTag} (not in the canonical pump master).`);
    }

    if (!row.readingDate) {
      errors.push("Reading Date is required.");
    } else if (!ISO_DATE_RE.test(row.readingDate)) {
      errors.push(`Reading Date "${row.readingDate}" is invalid.`);
    }

    // MWO-LTSA-CMON-EXCEL-IMPORT-001 -- an Excel-imported row's own
    // parse-time problems (invalid numeric text, an unrecognized leak
    // token) don't touch pumpTag/readingDate, so they would otherwise
    // slip past the checks above and show as falsely "Ready". Any
    // unresolved importErrors keep the row at ERROR until the user
    // edits it (BulkCMONReadingEditor clears importErrors on any
    // manual field change to that row, so a genuine correction always
    // clears this, never leaving a stale permanent block).
    const hasUnresolvedImportErrors = (row.importErrors || []).length > 0;
    const level = errors.length > 0 || hasUnresolvedImportErrors ? "ERROR" : "READY";
    results[row.id] = { errors, warnings: [], level };
  }

  const values = Object.values(results);
  const summary = {
    rows: rows.length,
    ready: values.filter((r) => r.level === "READY").length,
    warnings: 0,
    errors: values.filter((r) => r.level === "ERROR").length,
  };

  return { results, summary };
}

// Count of non-blank fields (measurements + operating state), for the
// compact "Measurements Summary" column -- never the full 37-field grid
// inline in the row table (Section 5's own "avoid an unusably-wide
// 30+ measurement-column table").
export function countRecordedMeasurements(measurements) {
  return Object.values(measurements || {}).filter((value) => value !== "").length;
}

export function toBulkAdHocPayloadRow(row) {
  return {
    asset_code: row.pumpTag,
    reading_date: row.readingDate || null,
    finding: row.finding.trim() ? row.finding.trim() : null,
    measurements: buildMeasurementsPayload(row.measurements),
  };
}

export function toBulkAdHocPayload(rows) {
  return { readings: rows.map(toBulkAdHocPayloadRow) };
}
