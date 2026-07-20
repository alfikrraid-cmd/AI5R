import { useState } from "react";
import { Tabs } from "../../../design-system";
import ExecutiveSummaryReport from "./ExecutiveSummaryReport";
import PumpHistoryReport from "./PumpHistoryReport";
import WorkOrderReport from "./WorkOrderReport";
import PreventiveMaintenanceReport from "./PreventiveMaintenanceReport";
import CorrectiveMaintenanceReport from "./CorrectiveMaintenanceReport";
import "./Reports.css";

/*
 * Labels are deliberately the full report names ("Work Order Report", not
 * "Work Order") — LTSAWorkspace's own outer tabs already use the short
 * names ("Work Order", "Preventive Maintenance", "Corrective
 * Maintenance"), and both tab bars are mounted simultaneously whenever
 * this "Reports" tab is active, so identical labels would be ambiguous
 * on screen and to assistive tech.
 */
const TABS = [
  { key: "executive-summary", label: "Executive Summary Report" },
  { key: "pump-history", label: "Pump History Report" },
  { key: "work-order", label: "Work Order Report" },
  { key: "pm", label: "Preventive Maintenance Report" },
  { key: "cm", label: "Corrective Maintenance Report" },
];

const PAGES = {
  "executive-summary": ExecutiveSummaryReport,
  "pump-history": PumpHistoryReport,
  "work-order": WorkOrderReport,
  pm: PreventiveMaintenanceReport,
  cm: CorrectiveMaintenanceReport,
};

/**
 * Manager-first reporting workspace: five print/PDF-ready reports, each
 * reusing existing LTSA components and sample-data derivation — no new
 * data model, no backend, no chart library. Mirrors the same internal
 * Tabs pattern already used by `LTSAWorkspace`.
 */
export default function ReportsWorkspace() {
  const [activeKey, setActiveKey] = useState("executive-summary");
  const ActiveReport = PAGES[activeKey];

  return (
    <div>
      <div className="no-print">
        <Tabs items={TABS} activeKey={activeKey} onChange={setActiveKey} />
      </div>

      <ActiveReport />
    </div>
  );
}
