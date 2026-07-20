import { PageHeader } from "../../../design-system";
import PrintButton from "../components/PrintButton";
import ReportGeneratedOn from "../components/ReportGeneratedOn";
import KpiCardGrid from "../components/KpiCardGrid";
import MaintenanceHealthPanel from "../components/MaintenanceHealthPanel";
import AttentionAssetList from "../components/AttentionAssetList";
import UpcomingMaintenanceList from "../components/UpcomingMaintenanceList";
import {
  buildAttentionAssets,
  buildKpiSummary,
  buildMaintenanceHealth,
  buildUpcomingMaintenance,
} from "../utils/executiveDashboard";

/**
 * Manager-facing report: the same KPI/health/attention/upcoming sections
 * as the Executive Dashboard, composed as a static print/PDF-ready
 * document rather than an interactive screen. Reuses the exact same
 * presentational components and data-derivation functions built for the
 * Executive Dashboard (MWO-LTSA-063) — no new aggregation logic.
 */
export default function ExecutiveSummaryReport() {
  const kpis = buildKpiSummary();
  const health = buildMaintenanceHealth();
  const attentionAssets = buildAttentionAssets();
  const upcomingMaintenance = buildUpcomingMaintenance();

  return (
    <div>
      <PageHeader
        title="Executive Summary Report"
        subtitle="LTSA Engineering — Manager Report"
        actions={<PrintButton />}
      />

      <ReportGeneratedOn />

      <KpiCardGrid kpis={kpis} />
      <MaintenanceHealthPanel health={health} />
      <AttentionAssetList assets={attentionAssets} />
      <UpcomingMaintenanceList schedules={upcomingMaintenance} />
    </div>
  );
}
