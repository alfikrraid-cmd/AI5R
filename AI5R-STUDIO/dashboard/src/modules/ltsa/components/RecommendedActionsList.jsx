import { Badge, Card, EmptyState } from "../../../design-system";
import spacing from "../../../design-system/theme/spacing";

export default function RecommendedActionsList({ actions }) {
  if (actions.length === 0) {
    return (
      <Card title="Recommended Actions">
        <EmptyState
          title="No immediate actions required"
          description="Every tracked metric is currently within normal range."
        />
      </Card>
    );
  }

  return (
    <Card title="Recommended Actions">
      <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}>
        {actions.map((action) => (
          <div key={action.id} style={{ display: "flex", alignItems: "center", gap: spacing.sm }}>
            <Badge variant={action.severity}>{action.severity.toUpperCase()}</Badge>
            <span>{action.text}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
