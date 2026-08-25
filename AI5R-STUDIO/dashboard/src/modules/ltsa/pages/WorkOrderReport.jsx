import { useEffect, useState } from "react";
import { EmptyState, PageHeader, Panel } from "../../../design-system";
import PrintButton from "../components/PrintButton";
import ReportGeneratedOn from "../components/ReportGeneratedOn";
import WorkOrderRegistryTable from "../components/WorkOrderRegistryTable";
import { getWorkOrders } from "../../../api/ai5rClient";
import { mapWorkOrderRecord, withResolvedArea } from "../utils/workOrderMapping";

/**
 * Manager-facing report: the full Work Order registry, reusing the exact
 * same `WorkOrderRegistryTable` component from the Work Order workspace,
 * rendered read-only (no selection) for print/PDF export. Sourced from the
 * canonical Work Order Registry API (APP-006) instead of sampleWorkOrders.js.
 */
export default function WorkOrderReport() {
  const [workOrders, setWorkOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;

    getWorkOrders()
      .then((records) => Promise.all(records.map(mapWorkOrderRecord).map(withResolvedArea)))
      .then((resolved) => {
        if (active) {
          setWorkOrders(resolved);
          setError(null);
        }
      })
      .catch(() => {
        if (active) {
          setError("Work orders could not be loaded.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div>
      <PageHeader
        title="Work Order Report"
        subtitle="LTSA Engineering - Manager Report"
        actions={<PrintButton />}
      />

      <ReportGeneratedOn />

      {loading ? (
        <Panel>
          <p>Loading work orders...</p>
        </Panel>
      ) : error ? (
        <Panel>
          <p role="alert">{error}</p>
        </Panel>
      ) : workOrders.length === 0 ? (
        <EmptyState
          title="No work orders available"
          description="The runtime work order registry currently has zero rows."
        />
      ) : (
        <WorkOrderRegistryTable workOrders={workOrders} selectedId={null} onSelect={() => {}} />
      )}
    </div>
  );
}
