import { Badge, Card } from "../../../design-system";
import spacing from "../../../design-system/theme/spacing";
import { criticalityBadgeVariant } from "../utils/pumpHealth";

export default function CriticalityDistributionList({ distribution }) {
  return (
    <Card title="Asset Criticality Distribution">
      <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.sm }}>
        {distribution.map((entry) => (
          <Badge key={entry.criticality} variant={criticalityBadgeVariant(entry.criticality)}>
            {entry.criticality}: {entry.count}
          </Badge>
        ))}
      </div>
    </Card>
  );
}
