import { PageHeader } from "../../../design-system";
import PrintButton from "../components/PrintButton";
import ReportGeneratedOn from "../components/ReportGeneratedOn";
import AssetSummaryCard from "../components/AssetSummaryCard";
import { buildAssetSummary, buildAssetTimeline, listAssets } from "../utils/maintenanceHistory";

/**
 * Manager-facing report: one Asset Summary per pump, plant-wide. Reuses
 * the exact same `AssetSummaryCard` and `buildAssetSummary`/
 * `buildAssetTimeline`/`listAssets` built for the Maintenance History
 * (Asset 360) workspace (MWO-LTSA-062), applied across every pump
 * instead of one selected asset.
 */
export default function PumpHistoryReport() {
  const assets = listAssets();

  return (
    <div>
      <PageHeader
        title="Pump History Report"
        subtitle="LTSA Engineering — Manager Report"
        actions={<PrintButton />}
      />

      <ReportGeneratedOn />

      {assets.map((pump) => (
        <AssetSummaryCard key={pump.tag} summary={buildAssetSummary(pump, buildAssetTimeline(pump.tag))} />
      ))}
    </div>
  );
}
