import { Table } from "../../../design-system";

// MECHANICAL-SEAL-DOMAIN-CONSOLIDATION-R1 -- Part B registry columns.
// Seal Code/Name dropped from the visible table (not deleted from the
// domain -- seal_code remains the real key everywhere else, seal_name
// remains real and independently used in SealDetailPanel/Knowledge/
// PhysicalSealWorkspace, per the Name Field Audit finding that it does
// not duplicate Seal Type). sealId/type/gpnJohnCrane are the columns
// mapSealRecord (sealMapping.js) now maps from the real, additive
// seal_id/seal_type/gpn_john_crane columns -- all three legitimately
// null for a seal this migration set could not safely assign, which
// _display below renders as "N/A", never blank/fabricated.
const COLUMNS = [
  { key: "sealIdDisplay", header: "Seal ID" },
  { key: "gpnDisplay", header: "GPN" },
  { key: "typeDisplay", header: "Seal Type" },
  { key: "sizeDisplay", header: "Size" },
  { key: "manufacturer", header: "Manufacturer" },
  { key: "status", header: "Status" },
];

const NOT_AVAILABLE = "N/A";

function toDisplay(value) {
  return value === null || value === undefined || value === "" ? NOT_AVAILABLE : value;
}

export default function SealRegistryTable({ seals, selectedCode, onSelect }) {
  const rows = (seals ?? []).map((seal) => ({
    ...seal,
    // Never falls back to seal.code: showing the legacy LTSA-SEAL-* code
    // under a "Seal ID" header would be exactly the conflation Part A
    // forbids (the legacy code is not the professional Seal ID).
    sealIdDisplay: toDisplay(seal.sealId),
    gpnDisplay: toDisplay(seal.gpnJohnCrane),
    typeDisplay: toDisplay(seal.type),
    sizeDisplay: toDisplay(seal.shaftSize),
  }));

  return (
    <Table
      columns={COLUMNS}
      data={rows}
      rowKey="code"
      selectedKey={selectedCode}
      onRowClick={(seal) => onSelect(seal.code)}
    />
  );
}
