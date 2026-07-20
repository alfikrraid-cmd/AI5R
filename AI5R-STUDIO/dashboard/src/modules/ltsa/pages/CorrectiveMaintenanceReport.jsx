import { PageHeader } from "../../../design-system";
import PrintButton from "../components/PrintButton";
import ReportGeneratedOn from "../components/ReportGeneratedOn";
import CMReportTable from "../components/CMReportTable";
import sampleCMReports from "../data/sampleCMReports";

/**
 * Manager-facing report: the full Corrective Maintenance registry,
 * reusing the exact same `CMReportTable` component from the Corrective
 * Maintenance workspace (MWO-LTSA-059), rendered read-only (no
 * selection) for print/PDF export.
 */
export default function CorrectiveMaintenanceReport() {
  return (
    <div>
      <PageHeader
        title="Corrective Maintenance Report"
        subtitle="LTSA Engineering — Manager Report"
        actions={<PrintButton />}
      />

      <ReportGeneratedOn />

      <CMReportTable cmReports={sampleCMReports} selectedId={null} onSelect={() => {}} />
    </div>
  );
}
