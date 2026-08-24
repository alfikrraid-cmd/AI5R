import { Card } from "../../../design-system";

// MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- bounded (BasicFleetOverview,
// GET /api/ltsa/fleet/overview) maintenance-activity summary: work-order
// status breakdown plus PM/CM counts. No per-pump fan-out, no optional
// data dependency -- always renders whenever the required overview does.
export default function MaintenanceActivityPanel({ overview }) {
  const workOrderEntries = Object.entries(overview.work_order_status_distribution ?? {});

  return (
    <Card title="Maintenance Activity">
      <div className="maintenance-activity-counts">
        <div className="maintenance-activity-count">
          <span className="maintenance-activity-count-label">PM Schedules</span>
          <strong>{overview.pm_schedule_count}</strong>
        </div>
        <div className="maintenance-activity-count">
          <span className="maintenance-activity-count-label">CM Reports</span>
          <strong>{overview.cm_report_count}</strong>
        </div>
        <div className="maintenance-activity-count">
          <span className="maintenance-activity-count-label">Work Orders</span>
          <strong>{overview.work_order_count}</strong>
        </div>
      </div>

      {workOrderEntries.length > 0 ? (
        <ul className="maintenance-activity-status-list">
          {workOrderEntries.map(([status, count]) => (
            <li key={status}>
              <span>{status}</span>
              <span>{count}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="maintenance-activity-empty">No work order status data available.</p>
      )}
    </Card>
  );
}
