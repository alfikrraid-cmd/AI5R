import { useEffect, useState } from "react";
import { EmptyState, PageHeader, Panel } from "../../../design-system";
import PrintButton from "../components/PrintButton";
import ReportGeneratedOn from "../components/ReportGeneratedOn";
import PMScheduleTable from "../components/PMScheduleTable";
import { getPMSchedules } from "../../../api/ai5rClient";
import { mapPMScheduleRecord, withResolvedArea } from "../utils/pmMapping";

export default function PreventiveMaintenanceReport() {
  const [pmSchedules, setPMSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;

    getPMSchedules()
      .then((records) => Promise.all(records.map(mapPMScheduleRecord).map(withResolvedArea)))
      .then((resolved) => {
        if (active) {
          setPMSchedules(resolved);
          setError(null);
        }
      })
      .catch(() => {
        if (active) {
          setError("PM schedules could not be loaded.");
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
        title="Preventive Maintenance Report"
        subtitle="LTSA Engineering - Manager Report"
        actions={<PrintButton />}
      />

      <ReportGeneratedOn />

      {loading ? (
        <Panel>
          <p>Loading PM schedules...</p>
        </Panel>
      ) : error ? (
        <Panel>
          <p role="alert">{error}</p>
        </Panel>
      ) : pmSchedules.length === 0 ? (
        <EmptyState
          title="No preventive maintenance schedules available"
          description="The runtime PM schedule registry currently has zero rows."
        />
      ) : (
        <PMScheduleTable pmSchedules={pmSchedules} selectedId={null} onSelect={() => {}} />
      )}
    </div>
  );
}
