/**
 * MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 -- derives the
 * Bill of Material table's columns from the row data actually present,
 * instead of InstallationOpenDesignView.jsx's previous hard-coded
 * no/partName/qty/workRequired shape (SCAN 001's own BOM structure only).
 * 3 of 5 golden-sample reports use a materially richer BOM (Drawing
 * Number/Material Code/Description/Material as distinct columns, up to
 * 38 rows); the JSONB storage was never lossy, but the UI silently hid
 * every one of those extra fields.
 *
 * BOM_KNOWN_COLUMNS is a superset of every BOM row-key observed across
 * all five golden samples, in a fixed, deterministic display order.
 * "no" and "item" are the same concept (row number) under two different
 * report-era key names -- both are listed since no golden sample uses
 * both at once, so nothing is ever suppressed by listing both.
 */
export const BOM_KNOWN_COLUMNS = [
  { key: "no", header: "No." },
  { key: "item", header: "Item" },
  { key: "drawingNumber", header: "Drawing Number" },
  { key: "materialCode", header: "Material Code" },
  { key: "partName", header: "Part Name" },
  { key: "description", header: "Description" },
  { key: "material", header: "Material" },
  { key: "qty", header: "Qty" },
  { key: "workRequired", header: "Work Required" },
  { key: "workRequiredDE", header: "Work Required (DE)" },
  { key: "workRequiredNDE", header: "Work Required (NDE)" },
];

function humanizeKey(key) {
  return key.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/^./, (c) => c.toUpperCase());
}

function hasValue(value) {
  return value !== null && value !== undefined && value !== "";
}

/**
 * Ordering: (1) known/common fields, in BOM_KNOWN_COLUMNS' fixed order,
 * (2) any additional legitimate source fields afterward, in first-seen
 * order -- both deterministic across renders of the same data. A column
 * is included only if at least one row in the whole table has a real
 * value for it ("empty columns... should not clutter the table"); a key
 * that is blank on some rows but populated on others still gets a column
 * (no source value silently disappears).
 */
export function computeBomColumns(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return [];
  }

  const presentKeys = new Set();
  const firstSeenOrder = [];
  for (const row of rows) {
    for (const key of Object.keys(row ?? {})) {
      if (hasValue(row[key]) && !presentKeys.has(key)) {
        presentKeys.add(key);
        firstSeenOrder.push(key);
      }
    }
  }

  const known = BOM_KNOWN_COLUMNS.filter((column) => presentKeys.has(column.key));
  const knownKeys = new Set(known.map((column) => column.key));
  const extra = firstSeenOrder
    .filter((key) => !knownKeys.has(key))
    .map((key) => ({ key, header: humanizeKey(key) }));

  return [...known, ...extra];
}

/** The Table design-system component keys each row on `item[rowKey]` --
 * "no" (SCAN-001-era reports) and "item" (SCAN-002-era reports onward)
 * are the two row-identity keys observed; whichever is actually present
 * is used, so every real BOM shape gets stable React keys. */
export function resolveBomRowKey(rows) {
  if (!Array.isArray(rows)) {
    return "no";
  }
  if (rows.some((row) => hasValue(row?.no))) {
    return "no";
  }
  if (rows.some((row) => hasValue(row?.item))) {
    return "item";
  }
  return "no";
}
