import { Table } from "../../../design-system";

const COLUMNS = [
  { key: "code", header: "Code" },
  { key: "tag", header: "Tag" },
  { key: "name", header: "Name" },
  { key: "manufacturer", header: "Manufacturer" },
  { key: "type", header: "Type" },
  { key: "status", header: "Status" },
];

export default function PumpRegistryTable({ pumps, selectedCode, onSelect }) {
  return (
    <Table
      columns={COLUMNS}
      data={pumps}
      rowKey="code"
      selectedKey={selectedCode}
      onRowClick={(pump) => onSelect(pump.code)}
    />
  );
}
