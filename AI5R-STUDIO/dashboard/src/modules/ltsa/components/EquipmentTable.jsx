import { Badge, EmptyState, Table } from "../../../design-system";
import { equipmentStatusVariant } from "../utils/equipmentFilters";

const COLUMNS = [
  { key: "equipment_id", header: "Equipment ID" },
  { key: "tag_number", header: "Tag Number" },
  { key: "equipment_name", header: "Equipment Name" },
  { key: "equipment_type", header: "Equipment Type" },
  { key: "area", header: "Area" },
  { key: "location", header: "Location" },
  { key: "manufacturer", header: "Manufacturer" },
  { key: "model", header: "Model" },
  {
    key: "status",
    header: "Status",
    render: (status) => (
      <Badge variant={equipmentStatusVariant(status)}>{status}</Badge>
    ),
  },
];

export default function EquipmentTable({ equipment, selectedId, onSelect }) {
  if (equipment.length === 0) {
    return (
      <EmptyState
        title="No equipment found"
        description="Adjust search or filters, or verify that equipment has been imported."
      />
    );
  }

  return (
    <div className="equipment-table-scroll">
      <Table
        columns={COLUMNS}
        data={equipment}
        rowKey="equipment_id"
        selectedKey={selectedId}
        onRowClick={onSelect}
      />
    </div>
  );
}
