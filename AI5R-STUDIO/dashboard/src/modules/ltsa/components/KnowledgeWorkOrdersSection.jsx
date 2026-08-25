import { Badge } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { EmptySection } from "./KnowledgeCard";

// MWO-LTSA-ASSET360-CONSOLIDATION-001 -- Section H, "WORK ORDERS". Already
// scoped to this pump only (workOrders comes from LTSAKnowledgeService's
// new work_orders field, filtered server-side by asset_code) -- never
// fleet-wide/unrelated WO, per the mission's explicit rule.
function statusGroup(workOrder) {
  if (workOrder.closedAt) return "Historical";
  if (workOrder.status === "IN_PROGRESS") return "In Progress";
  return "Open";
}

const GROUP_ORDER = ["Open", "In Progress", "Historical"];
const GROUP_VARIANT = { Open: "warning", "In Progress": "info", Historical: "success" };

export default function KnowledgeWorkOrdersSection({ workOrders }) {
  if (!workOrders || workOrders.length === 0) {
    return <EmptySection title="No Work Orders" description="No work orders recorded for this pump yet." />;
  }

  const grouped = GROUP_ORDER.map((group) => ({
    group,
    items: workOrders.filter((wo) => statusGroup(wo) === group),
  })).filter((entry) => entry.items.length > 0);

  return (
    <div>
      {grouped.map(({ group, items }) => (
        <div key={group} style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>
            {group} ({items.length})
          </div>
          {items.map((workOrder) => (
            <div key={workOrder.id} style={{ borderBottom: `1px solid ${colors.border}`, padding: `${spacing.xs}px 0` }}>
              <Badge variant={GROUP_VARIANT[group]}>{workOrder.id}</Badge> {workOrder.title ?? "N/A"}
              <div style={{ color: colors.textMuted, fontSize: 12 }}>
                {workOrder.workType ?? "N/A"} · Due {workOrder.dueDate ?? "N/A"} · {workOrder.assignedTechnician ?? "Unassigned"}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
