import { Table } from "../../../design-system";

const COLUMNS = [
  { key: "code", header: "Seal Code" },
  { key: "name", header: "Name" },
  { key: "type", header: "Type" },
  { key: "manufacturer", header: "Manufacturer" },
  { key: "status", header: "Status" },
];

export default function SealRegistryTable({ seals, selectedCode, onSelect }) {
  return (
    <Table
      columns={COLUMNS}
      data={seals}
      rowKey="code"
      selectedKey={selectedCode}
      onRowClick={(seal) => onSelect(seal.code)}
    />
  );
}
