import { PageHeader } from "../../../design-system";
import PrintButton from "../components/PrintButton";
import ReportGeneratedOn from "../components/ReportGeneratedOn";
import PMScheduleTable from "../components/PMScheduleTable";
import samplePMSchedules from "../data/samplePMSchedules";

/**
 * Manager-facing report: the full PM Schedule registry, reusing the exact
 * same `PMScheduleTable` component from the Preventive Maintenance
 * workspace (MWO-LTSA-058), rendered read-only (no selection) for
 * print/PDF export.
 */
export default function PreventiveMaintenanceReport() {
  return (
    <div>
      <PageHeader
        title="Preventive Maintenance Report"
        subtitle="LTSA Engineering — Manager Report"
        actions={<PrintButton />}
      />

      <ReportGeneratedOn />

      <PMScheduleTable pmSchedules={samplePMSchedules} selectedId={null} onSelect={() => {}} />
    </div>
  );
}
