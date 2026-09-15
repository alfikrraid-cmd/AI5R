import Badge from "../../../design-system/components/Badge";
import EmptyState from "../../../design-system/components/EmptyState";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";

export default function WorkforceBoardView({ board = {} }) {
  const columns = [
    {
      id: "published",
      title: "Available Queue",
      items: board.published || [],
      color: colors.info,
      badge: "PUBLISHED",
    },
    {
      id: "claimed",
      title: "In Progress",
      items: board.claimed || [],
      color: colors.purple,
      badge: "CLAIMED",
    },
    {
      id: "completed",
      title: "Completed / Review",
      items: board.completed || [],
      color: colors.warning,
      badge: "COMPLETED",
    },
    {
      id: "released",
      title: "Released",
      items: board.released || [],
      color: colors.success,
      badge: "RELEASED",
    },
  ];

  return (
    <div data-testid="workforce-board-view">
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: spacing.md,
          alignItems: "start",
        }}
      >
        {columns.map((col) => (
          <div
            key={col.id}
            data-testid={`board-column-${col.id}`}
            style={{
              background: colors.background,
              borderRadius: spacing.sm,
              border: `1px solid ${colors.border}`,
              padding: spacing.md,
              display: "flex",
              flexDirection: "column",
              gap: spacing.md,
              minHeight: 280,
            }}
          >
            {/* Column Header */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderBottom: `2px solid ${col.color}`,
                paddingBottom: spacing.xs,
              }}
            >
              <h3
                style={{
                  margin: 0,
                  fontSize: typography.size.sm,
                  fontWeight: typography.weight.bold,
                  color: colors.text,
                  textTransform: "uppercase",
                }}
              >
                {col.title}
              </h3>
              <Badge variant="purple">{col.items.length}</Badge>
            </div>

            {/* Column Cards */}
            <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}>
              {col.items.length === 0 ? (
                <EmptyState title={`No ${col.title.toLowerCase()} items`} />
              ) : (
                col.items.map((item) => {
                  const isProduction = Boolean(
                    item.is_production ||
                    item.metadata?.is_production ||
                    item.metadata?.requires_chief_approval
                  );
                  const isAwaitingChief =
                    col.id === "completed" && isProduction && !item.metadata?.chief_approval;

                  return (
                    <article
                      key={item.work_item_id}
                      data-testid={`work-item-${item.work_item_id}`}
                      style={{
                        background: colors.panel,
                        padding: spacing.sm,
                        borderRadius: spacing.xs,
                        border: `1px solid ${isAwaitingChief ? colors.warning : colors.border}`,
                        display: "flex",
                        flexDirection: "column",
                        gap: spacing.xs,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                        <span
                          style={{
                            fontSize: typography.size.xs,
                            fontWeight: typography.weight.bold,
                            color: colors.textMuted,
                          }}
                        >
                          {item.work_item_id.slice(0, 12)}
                        </span>
                        <div style={{ display: "flex", gap: spacing.xs / 2 }}>
                          {isProduction ? (
                            <Badge variant="danger">PRODUCTION</Badge>
                          ) : null}
                          <Badge variant="info">{item.assigned_position_id}</Badge>
                        </div>
                      </div>

                      <div
                        style={{
                          fontSize: typography.size.sm,
                          fontWeight: typography.weight.bold,
                          color: colors.text,
                        }}
                      >
                        {item.title}
                      </div>

                      {item.description ? (
                        <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
                          {item.description}
                        </div>
                      ) : null}

                      {/* Chief Gate Indicator */}
                      {isAwaitingChief ? (
                        <div
                          data-testid="chief-approval-gate-indicator"
                          style={{
                            background: "rgba(245, 158, 11, 0.15)",
                            border: `1px solid ${colors.warning}`,
                            borderRadius: spacing.xs,
                            padding: spacing.xs,
                            fontSize: typography.size.xs,
                            color: colors.warning,
                            fontWeight: typography.weight.bold,
                            display: "flex",
                            alignItems: "center",
                            gap: spacing.xs,
                          }}
                        >
                          ⚠️ CHIEF APPROVAL REQUIRED BEFORE RELEASE
                        </div>
                      ) : null}

                      {item.assigned_employee_id ? (
                        <div style={{ fontSize: typography.size.xs, color: colors.textMuted, marginTop: spacing.xs / 2 }}>
                          Assigned: <code>{item.assigned_employee_id.slice(0, 14)}</code>
                        </div>
                      ) : null}
                    </article>
                  );
                })
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

