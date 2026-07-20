import { Badge, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { criticalityBadgeVariant, statusBadgeVariant } from "../utils/pumpHealth";

export default function AttentionAssetList({ assets }) {
  if (assets.length === 0) {
    return (
      <Card title="Assets Requiring Attention">
        <EmptyState
          title="No assets currently require attention"
          description="Every high-criticality asset is running normally with no open work."
        />
      </Card>
    );
  }

  return (
    <Card title="Assets Requiring Attention">
      <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}>
        {assets.map((asset) => (
          <div
            key={asset.tag}
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: spacing.md,
              padding: spacing.sm,
              borderRadius: spacing.xs,
              border: `1px solid ${colors.border}`,
            }}
          >
            <div style={{ minWidth: 160 }}>
              <div style={{ fontWeight: "bold", color: colors.text }}>{asset.pump}</div>
              <div style={{ color: colors.textMuted, fontSize: 12 }}>{asset.tag}</div>
            </div>

            <Badge variant={criticalityBadgeVariant(asset.criticality)}>{asset.criticality}</Badge>
            <Badge variant={statusBadgeVariant(asset.status)}>{asset.status}</Badge>

            <div>
              <div style={{ color: colors.textMuted, fontSize: 12 }}>Open Work Orders</div>
              <div style={{ color: colors.text }}>{asset.openWorkOrders}</div>
            </div>

            <div>
              <div style={{ color: colors.textMuted, fontSize: 12 }}>Recent CM</div>
              <div style={{ color: colors.text }}>{asset.lastCorrectiveMaintenance ?? "None recorded"}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
