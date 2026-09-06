import {
  MEASUREMENT_PAIR_FIELDS,
  MEASUREMENT_SINGLE_FIELDS,
  LEAK_FIELD,
  parseOptionalNumber,
  emptyMeasurementFormValues,
} from "./conditionMonitoringMeasurementFields";
import { emptyBulkCmonRow } from "./cmonBulkReading";

// MWO-LTSA-CMON-EXCEL-IMPORT-001 -- Excel import mapping/validation/
// pump-resolution logic for Condition Monitoring readings. Deliberately
// pure and React-free, mirroring pmExcelImport.js's own convention, but
// NOT importing from that PM-specific module -- Phase 4F.1's own
// discovery explicitly warned against coupling CMON to PM business
// logic. The pump-tag normalization algorithm below is the same
// reference algorithm pmExcelImport.js already ported from copilot.py's
// _normalize_pump_tag() (proven by test_equipment_tag_entity_lock.py's
// own "110p12b" -> "110-P-12B" cases) -- reused by re-porting the same
// proven regex, not by cross-importing a PM module. The measurement
// catalog itself (MEASUREMENT_PAIR_FIELDS/MEASUREMENT_SINGLE_FIELDS/
// LEAK_FIELD/parseOptionalNumber) IS imported directly -- that module is
// CMON's own canonical source of truth, not a PM one, so this is not
// cross-domain coupling.

const REQUIRED_FIELDS = ["pumpTag"];

// Section 2/4 -- "Pump Tag*" is the only structurally-required column.
// Reading Date is expected (and included in the template) but its
// absence-per-row is reported by the EXISTING validateBulkCmonRows()
// the Bulk Editor already runs (Section 4: same "Reading Date is
// required" rule, never duplicated here) -- so an entirely-missing
// Reading Date column does not block the whole import, it just leaves
// every row's readingDate blank, which validateBulkCmonRows already
// flags per row.
const HEADER_ALIASES = {
  pumpTag: ["pump tag", "pump", "asset", "asset code", "equipment", "equipment tag"],
  readingDate: ["reading date", "date"],
  finding: ["finding / notes", "finding", "notes", "remark", "remarks", "keterangan"],
  pumpOperatingState: ["pump operating state", "operating state"],
};

// One alias pair per canonical DE/NDE measurement field, built from the
// SAME MEASUREMENT_PAIR_FIELDS list the Bulk Editor's measurement form
// already uses -- never a second, hand-typed 30-column list that could
// drift from the real catalog.
for (const field of MEASUREMENT_PAIR_FIELDS) {
  HEADER_ALIASES[field.deKey] = [`${field.group} de`.toLowerCase()];
  HEADER_ALIASES[field.ndeKey] = [`${field.group} nde`.toLowerCase()];
}
for (const field of MEASUREMENT_SINGLE_FIELDS) {
  HEADER_ALIASES[field.key] = [field.label.toLowerCase()];
}
HEADER_ALIASES[LEAK_FIELD.deKey] = [`${LEAK_FIELD.group} de`.toLowerCase()];
HEADER_ALIASES[LEAK_FIELD.ndeKey] = [`${LEAK_FIELD.group} nde`.toLowerCase()];

function normalizeHeaderText(raw) {
  return (raw || "")
    .replace(/\*/g, "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

// Unknown columns are ignored WITH a visible warning, never silently
// dropped without a trace; a missing Pump Tag column blocks the import
// entirely (the one genuinely structural requirement).
export function mapHeaders(headers) {
  const fieldToColumnIndex = {};
  const unknownColumns = [];

  headers.forEach((header, index) => {
    const normalized = normalizeHeaderText(header);
    if (!normalized) {
      return;
    }
    const field = Object.keys(HEADER_ALIASES).find((candidate) => HEADER_ALIASES[candidate].includes(normalized));
    if (field && !(field in fieldToColumnIndex)) {
      fieldToColumnIndex[field] = index;
    } else if (!field) {
      unknownColumns.push(header);
    }
  });

  const missingRequiredFields = REQUIRED_FIELDS.filter((field) => !(field in fieldToColumnIndex));
  return { fieldToColumnIndex, unknownColumns, missingRequiredFields };
}

// Ported from copilot.py's own _normalize_pump_tag()/_PUMP_TAG_PATTERN
// via pmExcelImport.js's own already-proven port -- same reference
// algorithm, reproduced here rather than cross-imported (Section:
// "never create CMON-depends-on-PM-domain coupling"). Never invents a
// pump: this only reconstructs the canonical hyphenated spelling of a
// tag whose digits+P+digits+suffix shape is already unambiguous -- the
// result must still exist in the canonical pump master to ever be used.
const PUMP_TAG_PATTERN = /^(\d+)\s*-?\s*P\s*-?\s*(\d+)\s*([A-Za-z]{1,3})$/i;

export function normalizePumpTagCandidate(raw) {
  const match = PUMP_TAG_PATTERN.exec((raw || "").trim());
  if (!match) {
    return null;
  }
  return `${match[1]}-P-${match[2]}${match[3].toUpperCase()}`;
}

// EXACT_MATCH / NORMALIZED_MATCH / NOT_FOUND -- same three-state
// contract as pmExcelImport.js's own resolvePumpTag(), reproduced here.
export function resolvePumpTag(raw, canonicalPumpTags) {
  const trimmed = (raw || "").trim();
  if (!trimmed) {
    return { status: "NOT_FOUND", assetCode: "" };
  }
  if (canonicalPumpTags.has(trimmed)) {
    return { status: "EXACT_MATCH", assetCode: trimmed };
  }
  const caseFolded = Array.from(canonicalPumpTags).find((tag) => tag.toUpperCase() === trimmed.toUpperCase());
  if (caseFolded) {
    return { status: "EXACT_MATCH", assetCode: caseFolded };
  }
  const normalized = normalizePumpTagCandidate(trimmed);
  if (normalized && canonicalPumpTags.has(normalized)) {
    return { status: "NORMALIZED_MATCH", assetCode: normalized };
  }
  return { status: "NOT_FOUND", assetCode: trimmed };
}

// Same DD/MM/YYYY-vs-ambiguous-MM/DD/YYYY policy as pmExcelImport.js's
// own parseExcelDate() (never silently guesses MM/DD/YYYY).
export function parseExcelDate(raw) {
  const trimmed = (raw || "").trim();
  if (!trimmed) {
    return { value: null, status: "BLANK" };
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return { value: trimmed, status: "OK" };
  }
  const slashMatch = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/);
  if (slashMatch) {
    const first = Number(slashMatch[1]);
    const second = Number(slashMatch[2]);
    let year = Number(slashMatch[3]);
    if (slashMatch[3].length === 2) {
      year += 2000;
    }
    if (first > 31 || second > 31) {
      return { value: null, status: "INVALID" };
    }
    if (first > 12 && second <= 12) {
      const day = String(first).padStart(2, "0");
      const month = String(second).padStart(2, "0");
      return { value: `${year}-${month}-${day}`, status: "OK" };
    }
    return { value: null, status: "AMBIGUOUS" };
  }
  return { value: null, status: "INVALID" };
}

// Section 4 -- deterministic leak alias map. Blank/"Not Recorded" ->
// null (never coerced to false); a small, fixed, documented set of
// equivalents for No Leak / Leak Detected; anything else is an error,
// row retained for correction.
const LEAK_NOT_RECORDED = new Set(["", "not recorded", "-", "n/a"]);
const LEAK_FALSE_ALIASES = new Set(["no leak", "false", "no", "0"]);
const LEAK_TRUE_ALIASES = new Set(["leak detected", "true", "yes", "1", "leak"]);

// Returns { value: null|false|true, status: "OK"|"ERROR" }. `status`
// distinguishes a genuinely-blank cell (never an error) from an
// unrecognized non-blank token (always an error, never guessed).
export function parseLeakCell(raw) {
  const normalized = (raw ?? "").trim().toLowerCase();
  if (LEAK_NOT_RECORDED.has(normalized)) {
    return { value: null, status: "OK" };
  }
  if (LEAK_FALSE_ALIASES.has(normalized)) {
    return { value: false, status: "OK" };
  }
  if (LEAK_TRUE_ALIASES.has(normalized)) {
    return { value: true, status: "OK" };
  }
  return { value: null, status: "ERROR" };
}

// Blank -> "" (validateBulkCmonRows' own null-safe form-value
// convention, matching emptyMeasurementFormValues()); a non-blank,
// non-numeric cell is reported as an error and the row's field is left
// blank (never guessed, never silently coerced to 0).
function parseMeasurementCell(raw) {
  const trimmed = (raw ?? "").trim();
  if (trimmed === "") {
    return { formValue: "", status: "OK" };
  }
  const parsed = parseOptionalNumber(trimmed);
  if (parsed === null || Number.isNaN(parsed) || !Number.isFinite(parsed)) {
    return { formValue: "", status: "ERROR" };
  }
  return { formValue: trimmed, status: "OK" };
}

function cellText(rawValues, fieldToColumnIndex, field) {
  const index = fieldToColumnIndex[field];
  if (index === undefined) {
    return "";
  }
  const value = rawValues[index];
  return value === null || value === undefined ? "" : String(value).trim();
}

// Maps ONE Excel data row into the exact same row shape emptyBulkCmonRow()
// produces, so imported and manually-added rows are indistinguishable to
// validateBulkCmonRows()/the Bulk Editor. A field that could not be
// resolved is left at its blank default so the existing
// validateBulkCmonRows() reports missing-required-field problems
// naturally; a cell that IS non-blank but invalid (bad pump, bad
// number, bad leak token) is reported here as an importError instead
// (rendered alongside, never instead of, live validation).
export function mapExcelRowToBulkRow(rawValues, fieldToColumnIndex, { canonicalPumpTags, rowNumber, makeRowId }) {
  const importErrors = [];

  const rawPumpTag = cellText(rawValues, fieldToColumnIndex, "pumpTag");
  const pumpResolution = resolvePumpTag(rawPumpTag, canonicalPumpTags);
  if (pumpResolution.status === "NOT_FOUND" && rawPumpTag) {
    importErrors.push(`Pump "${rawPumpTag}" not found.`);
  }

  const rawReadingDate = cellText(rawValues, fieldToColumnIndex, "readingDate");
  const dateResult = parseExcelDate(rawReadingDate);
  let readingDate = "";
  if (dateResult.status === "OK") {
    readingDate = dateResult.value;
  } else if (dateResult.status === "AMBIGUOUS") {
    importErrors.push(`Reading Date "${rawReadingDate}" is ambiguous.`);
  } else if (dateResult.status === "INVALID") {
    importErrors.push(`Reading Date "${rawReadingDate}" is invalid.`);
  }

  const measurements = emptyMeasurementFormValues();
  for (const field of MEASUREMENT_PAIR_FIELDS) {
    for (const key of [field.deKey, field.ndeKey]) {
      const raw = cellText(rawValues, fieldToColumnIndex, key);
      const result = parseMeasurementCell(raw);
      measurements[key] = result.formValue;
      if (result.status === "ERROR") {
        importErrors.push(`${field.group} ${key === field.deKey ? "DE" : "NDE"} "${raw}" is not a valid number.`);
      }
    }
  }
  for (const field of MEASUREMENT_SINGLE_FIELDS) {
    const raw = cellText(rawValues, fieldToColumnIndex, field.key);
    const result = parseMeasurementCell(raw);
    measurements[field.key] = result.formValue;
    if (result.status === "ERROR") {
      importErrors.push(`${field.label} "${raw}" is not a valid number.`);
    }
  }
  for (const [key, sideLabel] of [
    [LEAK_FIELD.deKey, "DE"],
    [LEAK_FIELD.ndeKey, "NDE"],
  ]) {
    const raw = cellText(rawValues, fieldToColumnIndex, key);
    const result = parseLeakCell(raw);
    measurements[key] = result.value === null ? "" : String(result.value);
    if (result.status === "ERROR") {
      importErrors.push(`${LEAK_FIELD.group} ${sideLabel} "${raw}" is not recognized.`);
    }
  }
  measurements.pumpOperatingState = cellText(rawValues, fieldToColumnIndex, "pumpOperatingState");

  const row = emptyBulkCmonRow(makeRowId(), {
    pumpTag: pumpResolution.assetCode,
    readingDate,
    finding: cellText(rawValues, fieldToColumnIndex, "finding"),
    measurements,
    source: "EXCEL_IMPORT",
    sourceRow: rowNumber,
    importErrors,
  });

  return row;
}

// Section 5/9 -- 1000-row cap, enforced here too (defense in depth
// alongside the backend's own cap).
export const MAX_IMPORT_ROWS = 1000;

// Structural failures (missing Pump Tag column, >1000 rows) block entry
// into the Bulk Editor entirely. Row-level problems (bad pump, bad
// number, bad leak token, bad date) are attached to individual rows and
// DO enter the Bulk Editor so the user can correct them -- no row is
// ever silently discarded.
export function buildImportPreview(grid, { canonicalPumpTags, makeRowId }) {
  const headers = grid?.headers || [];
  const dataRows = grid?.rows || [];

  if (dataRows.length > MAX_IMPORT_ROWS) {
    return {
      structuralError: `This file has ${dataRows.length} rows, more than the ${MAX_IMPORT_ROWS}-row limit -- split it into smaller files.`,
    };
  }

  const { fieldToColumnIndex, unknownColumns, missingRequiredFields } = mapHeaders(headers);
  if (missingRequiredFields.length > 0) {
    return { structuralError: "Missing required column: Pump Tag." };
  }

  const rows = dataRows.map((rawValues, index) =>
    mapExcelRowToBulkRow(rawValues, fieldToColumnIndex, {
      canonicalPumpTags,
      rowNumber: index + 2, // +1 header row, +1 for 1-based Excel row numbers
      makeRowId,
    })
  );

  const warnings = unknownColumns.map((column) => `Column "${column}" is not recognized and was ignored.`);
  const errors = rows.reduce((count, row) => count + row.importErrors.length, 0);

  return {
    structuralError: null,
    unknownColumns,
    mappedColumns: Object.keys(fieldToColumnIndex),
    warnings,
    rows,
    rowCount: rows.length,
    importErrorCount: errors,
  };
}
