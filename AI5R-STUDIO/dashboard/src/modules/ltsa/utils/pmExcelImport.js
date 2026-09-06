import { PM_ACTIVITY_FAMILIES } from "./pmActivityCatalog";
import { emptyBulkRow } from "./pmBulkSchedule";

// AI5R-PHASE4E4 -- Excel import mapping/validation/pump-resolution logic.
// Deliberately pure and React-free (mirrors pmBulkSchedule.js's own
// convention) so every rule here is directly unit-testable. The backend
// (API/pm_schedule_excel_import.py) does DECODE ONLY -- turns .xlsx bytes
// into a {headers, rows} JSON grid -- every business rule below runs
// here, client-side, against data already in the browser (the canonical
// pump list from getPumps(), the same one AssetSelector/the manual bulk
// editor already use). See that Python module's own header comment for
// why decoding itself could not stay client-side (every candidate JS
// .xlsx library carries either an unpatched high-severity CVE or a new
// transitive one, while openpyxl is already a vetted, in-use dependency
// for this exact domain).

const REQUIRED_FIELDS = ["pumpTag", "frequency", "startDate"];

// Section E -- canonical field -> accepted header aliases, matched
// case-insensitively after trimming and collapsing whitespace. Never
// fuzzy beyond this fixed list (Section E: "Do not fuzzy-map
// dangerously").
const HEADER_ALIASES = {
  pumpTag: ["pump tag", "pump", "asset", "asset code", "equipment", "equipment tag"],
  frequency: ["frequency", "interval"],
  startDate: ["start date", "effective date"],
  plannedActivities: ["planned activities", "activities"],
  technician: ["assigned technician", "technician"],
  duration: ["estimated duration", "duration", "duration minutes"],
  notes: ["notes", "remark", "remarks", "keterangan"],
};

function normalizeHeaderText(raw) {
  return (raw || "")
    .replace(/\*/g, "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

// Section E -- unknown columns are ignored WITH a visible warning, never
// silently dropped without a trace; missing required columns block the
// import entirely (Section J).
export function mapHeaders(headers) {
  const fieldToColumnIndex = {};
  const unknownColumns = [];

  headers.forEach((header, index) => {
    const normalized = normalizeHeaderText(header);
    if (!normalized) {
      return;
    }
    const field = Object.keys(HEADER_ALIASES).find((candidate) =>
      HEADER_ALIASES[candidate].includes(normalized)
    );
    if (field && !(field in fieldToColumnIndex)) {
      fieldToColumnIndex[field] = index;
    } else if (!field) {
      unknownColumns.push(header);
    }
  });

  const missingRequiredFields = REQUIRED_FIELDS.filter((field) => !(field in fieldToColumnIndex));
  return { fieldToColumnIndex, unknownColumns, missingRequiredFields };
}

// AI5R-PHASE4E4, Section F -- ported from CORE-SERVICES/BACKEND-API/
// routers/copilot.py's own _normalize_pump_tag()/_PUMP_TAG_PATTERN
// (proven by CORE-SERVICES/API/TESTS/test_equipment_tag_entity_lock.py's
// own "110p12b" -> "110-P-12B" parametrized cases) -- the ONLY existing
// AI5R normalization that proves compact-tag reconstruction, per this
// mission's own "ONLY IF existing AI5R normalization already proves this
// mapping" constraint. Never invents a pump: this only RECONSTRUCTS the
// canonical hyphenated spelling of a tag whose digits+P+digits+suffix
// shape is already unambiguous -- the result must still exist in the
// canonical pump master to ever be used (see resolvePumpTag below).
const PUMP_TAG_PATTERN = /^(\d+)\s*-?\s*P\s*-?\s*(\d+)\s*([A-Za-z]{1,3})$/i;

export function normalizePumpTagCandidate(raw) {
  const match = PUMP_TAG_PATTERN.exec((raw || "").trim());
  if (!match) {
    return null;
  }
  return `${match[1]}-P-${match[2]}${match[3].toUpperCase()}`;
}

// Section F -- EXACT_MATCH / NORMALIZED_MATCH / NOT_FOUND. Trim +
// case-fold are treated as EXACT_MATCH (pure typography, matching
// historical_pm_cmon_extraction.py's match_pump_tag() own established
// philosophy: "pure whitespace/typography differences... are NOT an
// identity ambiguity"); the regex reconstruction above is
// NORMALIZED_MATCH. A NOT_FOUND result still returns the caller's
// trimmed raw value as assetCode, so validateBulkRows' existing "Unknown
// pump: X" check fires with the useful original value.
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

// Section G -- deterministic alias map; also accepts the canonical
// values themselves case-insensitively.
const FREQUENCY_ALIAS_SOURCE = {
  DAILY: ["daily", "harian"],
  WEEKLY: ["weekly", "mingguan"],
  MONTHLY: ["monthly", "bulanan"],
  RUNTIME_BASED: ["runtime based", "runtime-based", "runtime", "operating hours"],
};

const FREQUENCY_LOOKUP = new Map();
for (const [canonical, aliases] of Object.entries(FREQUENCY_ALIAS_SOURCE)) {
  FREQUENCY_LOOKUP.set(canonical.toLowerCase(), canonical);
  for (const alias of aliases) {
    FREQUENCY_LOOKUP.set(alias, canonical);
  }
}

export function parseFrequency(raw) {
  const normalized = (raw || "").trim().toLowerCase().replace(/\s+/g, " ");
  return FREQUENCY_LOOKUP.get(normalized) || null;
}

// Section H -- YYYY-MM-DD and DD/MM/YYYY accepted; MM/DD/YYYY is never
// silently guessed. Policy for a two-slash date "A/B/YYYY": if A > 12 it
// can only be a day (DD/MM, unambiguous); otherwise (A<=12 and B<=12, OR
// A<=12 and B>12 which would require the MM/DD reading this mission
// explicitly forbids) it is treated as AMBIGUOUS/INVALID and rejected
// for human correction, exactly matching the mission's own worked
// example ("09/10/26" -- both <=12 -- is ambiguous).
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

// Section I -- label -> canonical catalog code, built from the SAME
// PM_ACTIVITY_FAMILIES catalog the manual bulk editor already uses (no
// second taxonomy). Accepts both the mission's own "Family General/DE/
// NDE" label form AND the catalog's existing UI description form
// ("... DE Side"/"... NDE Side", plus the bare family name for the
// General variant). WCH/Water-Cooled Heat Exchanger are never in this
// catalog at all, so they are unreachable here by construction -- not a
// special-cased rejection, an absence.
const ACTIVITY_LABEL_LOOKUP = new Map();
for (const family of PM_ACTIVITY_FAMILIES) {
  for (const variant of family.variants) {
    const sideWord = variant.side ?? "General";
    ACTIVITY_LABEL_LOOKUP.set(`${family.family} ${sideWord}`.toLowerCase(), variant.code);
    ACTIVITY_LABEL_LOOKUP.set(variant.label.toLowerCase(), variant.code);
  }
}

// Section I -- blank Activities is valid ([]); unknown tokens (including
// "Reservoir DE"/"Reservoir NDE", which simply do not exist in the
// catalog above) are reported individually, never silently dropped.
export function parsePlannedActivities(raw) {
  const trimmed = (raw || "").trim();
  if (!trimmed) {
    return { plannedMap: {}, unknownTokens: [] };
  }
  const tokens = trimmed
    .split(";")
    .map((token) => token.trim())
    .filter(Boolean);

  const plannedMap = {};
  const unknownTokens = [];
  for (const token of tokens) {
    const code = ACTIVITY_LABEL_LOOKUP.get(token.toLowerCase());
    if (code) {
      plannedMap[code] = true;
    } else {
      unknownTokens.push(token);
    }
  }
  return { plannedMap, unknownTokens };
}

function cellText(rawValues, fieldToColumnIndex, field) {
  const index = fieldToColumnIndex[field];
  if (index === undefined) {
    return "";
  }
  const value = rawValues[index];
  return value === null || value === undefined ? "" : String(value).trim();
}

// Section F/G/H/I combined -- maps ONE Excel data row into the exact
// same row shape emptyBulkRow() produces, so imported and manually-added
// rows are indistinguishable to validateBulkRows()/the Bulk Editor
// (Section K). A field that could not be resolved is left as the
// best-effort RAW value (pump, frequency) so the existing 4E.3
// validateBulkRows() reports it naturally (Section K: "normal 4E.3
// validation applies"); Start Date and Planned Activities have no such
// slot for an invalid raw string, so their problems go into
// `importErrors` instead (rendered alongside, never instead of, live
// validation -- see BulkPMScheduleEditor's Validation column).
export function mapExcelRowToBulkRow(rawValues, fieldToColumnIndex, { canonicalPumpTags, rowNumber, makeRowId }) {
  const importErrors = [];

  const rawPumpTag = cellText(rawValues, fieldToColumnIndex, "pumpTag");
  const pumpResolution = resolvePumpTag(rawPumpTag, canonicalPumpTags);
  if (pumpResolution.status === "NOT_FOUND" && rawPumpTag) {
    importErrors.push(`Pump "${rawPumpTag}" not found.`);
  }

  const rawFrequency = cellText(rawValues, fieldToColumnIndex, "frequency");
  const parsedFrequency = parseFrequency(rawFrequency);
  const frequency = parsedFrequency || rawFrequency;
  if (rawFrequency && !parsedFrequency) {
    importErrors.push(`Frequency "${rawFrequency}" is unsupported.`);
  }

  const rawStartDate = cellText(rawValues, fieldToColumnIndex, "startDate");
  const dateResult = parseExcelDate(rawStartDate);
  let startDate = "";
  if (dateResult.status === "OK") {
    startDate = dateResult.value;
  } else if (dateResult.status === "AMBIGUOUS") {
    importErrors.push(`Start Date "${rawStartDate}" is ambiguous.`);
  } else if (dateResult.status === "INVALID") {
    importErrors.push(`Start Date "${rawStartDate}" is invalid.`);
  }

  const rawActivities = cellText(rawValues, fieldToColumnIndex, "plannedActivities");
  const { plannedMap, unknownTokens } = parsePlannedActivities(rawActivities);
  for (const token of unknownTokens) {
    importErrors.push(`Activity "${token}" is invalid.`);
  }

  const row = emptyBulkRow(makeRowId(), {
    pumpTag: pumpResolution.assetCode,
    frequency,
    startDate,
    plannedMap,
    technician: cellText(rawValues, fieldToColumnIndex, "technician"),
    duration: cellText(rawValues, fieldToColumnIndex, "duration"),
    notes: cellText(rawValues, fieldToColumnIndex, "notes"),
    source: "EXCEL_IMPORT",
    sourceRow: rowNumber,
    importErrors,
  });

  return row;
}

// Section C/J -- 1000-row cap, enforced here too (defense in depth
// alongside the backend's own cap in pm_schedule_excel_import.py).
export const MAX_IMPORT_ROWS = 1000;

// Section J -- the whole-workbook preview: structural failures (missing
// required columns, too many rows) block entry into the Bulk Editor
// entirely; row-level problems (Section G/H/I) are attached to
// individual rows and DO enter the Bulk Editor so the user can correct
// them manually (Section J: "Do not discard invalid rows silently").
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
    const labels = { pumpTag: "Pump Tag", frequency: "Frequency", startDate: "Start Date" };
    return {
      structuralError: `Missing required column(s): ${missingRequiredFields.map((f) => labels[f]).join(", ")}.`,
    };
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
