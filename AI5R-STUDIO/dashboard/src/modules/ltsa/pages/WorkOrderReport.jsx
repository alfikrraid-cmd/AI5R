import { PageHeader } from "../../../design-system";
import PrintButton from "../components/PrintButton";
import ReportGeneratedOn from "../components/ReportGeneratedOn";
import WorkOrderRegistryTable from "../components/WorkOrderRegistryTable";
import sampleWorkOrders from "../data/sampleWorkOrders";

/**
 * Manager-facing report: the full Work Order registry, reusing the exact
 * same `WorkOrderRegistryTable` component from the Work Order workspace
 * (MWO-LTSA-057), rendered read-only (no selection) for print/PDF export.
 */
export default function WorkOrderReport() {
  return (
    <div>
      <PageHeader
        title="Work Order Report"
        subtitle="LTSA Engineering — Manager Report"
        actions={<PrintButton />}
      />

      <ReportGeneratedOn />

      <WorkOrderRegistryTable workOrders={sampleWorkOrders} selectedId={null} onSelect={() => {}} />
    </div>
  );
}
