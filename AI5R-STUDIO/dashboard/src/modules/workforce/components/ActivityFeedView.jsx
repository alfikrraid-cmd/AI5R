import Badge from "../../../design-system/components/Badge";
import EmptyState from "../../../design-system/components/EmptyState";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";

const PHASE_BADGES = {
  THINKING: "purple",
  EXECUTING: "info",
  REVIEWING: "warning",
  LEARNING: "success",
  COMPLETED: "success",
  RECEIVED_WORK: "info",
};

export default function ActivityFeedView({ activities = [] }) {
  if (!activities || activities.length === 0) {
    return (
      <div data-testid="activity-feed-empty" style={{ padding: spacing.lg }}>
        <EmptyState title="No activities recorded yet" />
      </div>
    );
  }

  return (
    <div
      data-testid="workforce-activity-feed"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: spacing.sm,
      }}
    >
      {activities.map((act) => {
        const phaseVariant = PHASE_BADGES[act.status] || PHASE_BADGES[act.activity_type] || "info";

        return (
          <div
            key={act.activity_id}
            data-testid={`activity-item-${act.activity_id}`}
            style={{
              background: colors.panel,
              borderRadius: spacing.xs,
              border: `1px solid ${colors.border}`,
              padding: spacing.md,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: spacing.md,
            }}
          >
            {/* Left: Indicator, Message, Context */}
            <div style={{ display: "flex", alignItems: "center", gap: spacing.md }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  background: colors.border,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: typography.size.sm,
                  fontWeight: typography.weight.bold,
                  color: colors.text,
                  flexShrink: 0,
                }}
              >
                ⚡
              </div>

              <div>
                <div style={{ display: "flex", alignItems: "center", gap: spacing.xs }}>
                  <span style={{ fontWeight: typography.weight.bold, color: colors.text, fontSize: typography.size.sm }}>
                    {act.message || act.activity_type}
                  </span>
                  <Badge variant={phaseVariant}>{act.status}</Badge>
                </div>

                <div style={{ fontSize: typography.size.xs, color: colors.textMuted, marginTop: spacing.xs / 2 }}>
                  Employee: <code>{act.employee_id}</code>
                  {act.work_item_id ? (
                    <span> | Task: <code>{act.work_item_id.slice(0, 14)}</code></span>
                  ) : null}
                </div>
              </div>
            </div>

            {/* Right: Progress & Timestamp */}
            <div style={{ textAlign: "right", flexShrink: 0 }}>
              <div style={{ fontSize: typography.size.sm, fontWeight: typography.weight.bold, color: colors.text }}>
                {act.progress}%
              </div>
              <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
                {act.updated_at ? new Date(act.updated_at).toLocaleTimeString() : ""}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

