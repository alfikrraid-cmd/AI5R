import { Badge, EmptyState, Panel } from "../../../design-system";
import {
  priorityBadgeVariant as workOrderPriorityVariant,
  statusBadgeVariant as workOrderStatusVariant,
} from "../utils/workOrderStatus";

function WorkOrderInspector({ workOrder }) {
  return (
    <section className="work-order-detail" aria-label="Work order inspector">
      <div className="work-order-detail-heading">
        <h5>Work Order {workOrder.work_order_id}</h5>
        <Badge variant={workOrderStatusVariant(workOrder.status)}>
          {workOrder.status}
        </Badge>
      </div>
      <dl>
        <div><dt>Priority</dt><dd><Badge variant={workOrderPriorityVariant(workOrder.priority)}>{workOrder.priority}</Badge></dd></div>
        <div><dt>Assigned engineer</dt><dd>{workOrder.assigned_engineer || "Unassigned"}</dd></div>
        <div><dt>Target date</dt><dd>{workOrder.target_date || "Not scheduled"}</dd></div>
        <div><dt>Completion date</dt><dd>{workOrder.completion_date || "Not completed"}</dd></div>
        <div><dt>Progress</dt><dd>{workOrder.progress ?? 0}%</dd></div>
      </dl>
    </section>
  );
}

export default function WorkOrderPanel({
  workOrders,
  loading,
  error,
  selectedWorkOrder,
  onSelect,
}) {
  if (loading) return <Panel><p>Loading work orders...</p></Panel>;
  if (error) return <Panel><p role="alert">{error}</p></Panel>;
  if (workOrders.length === 0) {
    return <EmptyState title="No work orders recorded" description="This finding does not have an existing work order." />;
  }

  return (
    <section className="work-order-panel" aria-label="Finding work orders">
      <h5>Existing work orders</h5>
      <div className="work-order-list">
        {workOrders.map((workOrder) => (
          <button
            key={workOrder.work_order_id}
            type="button"
            aria-label={`${workOrder.work_order_id} ${workOrder.status}`}
            aria-pressed={workOrder.work_order_id === selectedWorkOrder?.work_order_id}
            onClick={() => onSelect(workOrder)}
          >
            <span><strong>{workOrder.work_order_id}</strong><small>{workOrder.assigned_engineer || "Unassigned"}</small></span>
            <Badge variant={workOrderPriorityVariant(workOrder.priority)}>{workOrder.priority}</Badge>
          </button>
        ))}
      </div>
      {selectedWorkOrder ? <WorkOrderInspector workOrder={selectedWorkOrder} /> : null}
    </section>
  );
}
