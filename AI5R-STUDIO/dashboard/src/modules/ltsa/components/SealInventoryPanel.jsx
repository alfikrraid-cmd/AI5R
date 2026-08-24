import { Card } from "../../../design-system";

// MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- bounded (BasicFleetOverview)
// seal-inventory summary. low_stock_seal_count is None (rendered "N/A")
// whenever no seal stock record carried both quantity_on_hand and
// reorder_point -- never guessed as 0.
export default function SealInventoryPanel({ overview }) {
  return (
    <Card title="Seal Inventory">
      <div className="seal-inventory-counts">
        <div className="seal-inventory-count">
          <span className="seal-inventory-count-label">Stock Records</span>
          <strong>{overview.seal_stock_count}</strong>
        </div>
        <div className="seal-inventory-count seal-inventory-count-low">
          <span className="seal-inventory-count-label">Low Stock</span>
          <strong>{overview.low_stock_seal_count ?? "N/A"}</strong>
        </div>
      </div>
    </Card>
  );
}
