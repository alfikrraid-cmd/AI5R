import { Button, Card, EmptyState, Table } from "../../../design-system";

/**
 * BOM (RC-003B §5). Reuses the design-system Table (already used by
 * DrawingRevisionPanel/PumpDetailPanel/WorkOrderDetailPanel for row
 * lists) -- no new table component. Stock Status is explicitly a
 * placeholder string (no Inventory backend exists); "Deep-link" is a
 * disabled placeholder button per part row, per RC-003B's own
 * instruction ("Deep-link placeholder").
 */
export default function DrawingBomTable({ drawing }) {
  if (!drawing) {
    return (
      <Card title="BOM">
        <EmptyState title="No BOM to show" description="Bill of materials appears here once a drawing is opened." />
      </Card>
    );
  }

  if (drawing.bom.length === 0) {
    return (
      <Card title="BOM">
        <EmptyState
          title="No bill of materials linked to this drawing yet"
          description="BOM lines appear here once this drawing's part list is recorded."
        />
      </Card>
    );
  }

  return (
    <Card title="BOM">
      <Table
        rowKey="partNumber"
        data={drawing.bom}
        columns={[
          { key: "partNumber", header: "Part Number" },
          { key: "description", header: "Description" },
          { key: "qty", header: "Qty" },
          { key: "material", header: "Material" },
          { key: "oemNumber", header: "OEM Number" },
          { key: "stockStatus", header: "Stock Status" },
          {
            key: "deepLink",
            header: "",
            render: () => <Button disabled>Open in Inventory (Coming soon)</Button>,
          },
        ]}
      />
    </Card>
  );
}
