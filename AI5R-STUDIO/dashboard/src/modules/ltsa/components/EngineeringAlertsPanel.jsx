import { Badge, Card, EmptyState } from "../../../design-system";
import spacing from "../../../design-system/theme/spacing";

/**
 * RC-002 (Executive Dashboard React Implementation). Reuses the same
 * alert-card visual pattern already established by AttentionAssetList
 * (Card + Badge), but at plant-wide count granularity rather than
 * per-asset rows -- distinct presentation of buildEngineeringAlerts()'s
 * counts, not a second copy of AttentionAssetList's own per-asset list.
 */
export default function EngineeringAlertsPanel({ alerts }) {
  const items = [
    { key: "overduePM", label: "Overdue PM", count: alerts.overduePM },
    { key: "criticalOpenCM", label: "Critical Open Corrective Maintenance", count: alerts.criticalOpenCM },
    { key: "criticalOpenWorkOrders", label: "Critical Open Work Orders", count: alerts.criticalOpenWorkOrders },
  ].filter((item) => item.count > 0);

  if (items.length === 0) {
    return (
      <Card title="Engineering Alerts">
        <EmptyState
          title="No active engineering alerts"
          description="Every tracked overdue/critical condition is currently clear."
        />
      </Card>
    );
  }

  return (
    <Card title="Engineering Alerts">
      <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.sm }}>
        {items.map((item) => (
          <Badge key={item.key} variant="danger">
            {item.label}: {item.count}
          </Badge>
        ))}
      </div>
    </Card>
  );
}
