import { useEffect, useState } from "react";
import { EmptyState, PageHeader, Panel } from "../../../design-system";
import PrintButton from "../components/PrintButton";
import ReportGeneratedOn from "../components/ReportGeneratedOn";
import CMReportTable from "../components/CMReportTable";
import { getCMReports } from "../../../api/ai5rClient";
import { mapCMReportRecord } from "../utils/cmMapping";

export default function CorrectiveMaintenanceReport() {
  const [cmReports, setCMReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;

    getCMReports({ timeoutMs: 5000 })
      .then((records) => records.map(mapCMReportRecord))
      .then((resolved) => {
        if (active) {
          setCMReports(resolved);
          setError(null);
        }
      })
      .catch(() => {
        if (active) {
          setError("CM reports could not be loaded.");
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
        title="Corrective Maintenance Report"
        subtitle="LTSA Engineering - Manager Report"
        actions={<PrintButton />}
      />

      <ReportGeneratedOn />

      {loading ? (
        <Panel>
          <p>Loading CM reports...</p>
        </Panel>
      ) : error ? (
        <Panel>
          <p role="alert">{error}</p>
        </Panel>
      ) : cmReports.length === 0 ? (
        <EmptyState
          title="No corrective maintenance reports available"
          description="The runtime CM report registry currently has zero rows."
        />
      ) : (
        <CMReportTable cmReports={cmReports} selectedId={null} onSelect={() => {}} />
      )}
    </div>
  );
}
