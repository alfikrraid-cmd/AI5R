import { Badge, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import {
  eventStatusBadgeVariant,
  eventStatusLabel,
  eventTypeBadgeVariant,
  eventTypeLabel,
} from "../utils/maintenanceHistory";

export default function RecentActivityFeed({ activities }) {
  if (activities.length === 0) {
    return (
      <Card title="Recent Activities">
        <EmptyState title="No recent activity" description="No maintenance events have been recorded." />
      </Card>
    );
  }

  return (
    <Card title="Recent Activities">
      <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}>
        {activities.map((event) => (
          <div
            key={event.id}
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: spacing.sm,
              padding: `${spacing.xs}px 0`,
              borderBottom: `1px solid ${colors.border}`,
            }}
          >
            <div style={{ color: colors.textMuted, fontSize: 12, minWidth: 90 }}>{event.date ?? "—"}</div>
            <Badge variant={eventTypeBadgeVariant(event.type)}>{eventTypeLabel(event.type)}</Badge>

            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ fontWeight: "bold", color: colors.text }}>{event.id}</div>
              <div style={{ fontSize: 13, color: colors.text }}>{event.title}</div>
            </div>

            <Badge variant={eventStatusBadgeVariant(event)}>{eventStatusLabel(event)}</Badge>
          </div>
        ))}
      </div>
    </Card>
  );
}
