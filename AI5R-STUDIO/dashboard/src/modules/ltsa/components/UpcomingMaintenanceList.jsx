import { Badge, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { statusBadgeVariant, statusLabel } from "../utils/pmStatus";

export default function UpcomingMaintenanceList({ schedules }) {
  if (schedules.length === 0) {
    return (
      <Card title="Upcoming Maintenance">
        <EmptyState
          title="Nothing due soon"
          description="No preventive maintenance is currently due soon or overdue."
        />
      </Card>
    );
  }

  return (
    <Card title="Upcoming Maintenance">
      <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}>
        {schedules.map((pm) => (
          <div
            key={pm.id}
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
            <div style={{ minWidth: 200 }}>
              <div style={{ fontWeight: "bold", color: colors.text }}>{pm.procedure}</div>
              <div style={{ color: colors.textMuted, fontSize: 12 }}>
                {pm.id} · {pm.equipmentTag}
              </div>
            </div>

            <div>
              <div style={{ color: colors.textMuted, fontSize: 12 }}>Next Due</div>
              <div style={{ color: colors.text }}>{pm.nextDue}</div>
            </div>

            <div>
              <div style={{ color: colors.textMuted, fontSize: 12 }}>Assigned Technician</div>
              <div style={{ color: colors.text }}>{pm.assignedTechnician}</div>
            </div>

            <Badge variant={statusBadgeVariant(pm.status)}>{statusLabel(pm.status)}</Badge>
          </div>
        ))}
      </div>
    </Card>
  );
}
