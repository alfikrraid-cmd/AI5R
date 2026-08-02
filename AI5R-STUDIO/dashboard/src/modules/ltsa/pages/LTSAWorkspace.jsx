import { useState } from "react";
import { Tabs } from "../../../design-system";
import ExecutiveDashboard from "./ExecutiveDashboard";
import Equipment from "./Equipment";
import Pump from "./Pump";
import WorkOrder from "./WorkOrder";
import PM from "./PM";
import CM from "./CM";
import ConditionMonitoring from "./ConditionMonitoring";
import ConditionMonitoringWorkspace from "./ConditionMonitoringWorkspace";
import MaintenanceHistory from "./MaintenanceHistory";
import PMWorkOrderWorkspace from "./PMWorkOrderWorkspace";
import ReportsWorkspace from "./ReportsWorkspace";
import AnalyticsWorkspace from "./AnalyticsWorkspace";
import "./LTSAWorkspace.css";

// "history"'s label is "Asset 360" (renamed under APP-ASSET360-001) --
// the tab's own page already called itself that in its subtitle, and
// QuickNavigationPanel's button already said "Open Asset 360"; only this
// label had not caught up (DISCOVERY-ASSET360-UI-001's key finding). The
// key itself stays "history", unchanged, so every existing onNavigate
// ("history") call site keeps working.
//
// "cmon" (APP-CMON-001, per ADR-CONDITION-MONITORING-001) -- key
// deliberately not "cm", to avoid colliding with the existing Corrective
// Maintenance tab, the same naming discipline this whole engineering line
// has carried since DISCOVERY-LTSA-REPORT-001 first flagged the "CM"
// acronym collision.
const TABS = [
  { key: "dashboard", label: "Executive Dashboard" },
  { key: "equipment", label: "Equipment" },
  { key: "pump", label: "Pump" },
  { key: "workorder", label: "Work Order" },
  { key: "pm", label: "Preventive Maintenance" },
  { key: "cm", label: "Corrective Maintenance" },
  { key: "cmon", label: "Condition Monitoring" },
  { key: "history", label: "Asset 360" },
  { key: "reports", label: "Reports" },
  { key: "analytics", label: "Analytics" },
];

// "pm-workspace" (PM Work Order Workspace) is deep-link-only, not a TABS
// entry -- like the PM Workspace design itself, it's scoped to one Work
// Order (navContext.workOrderId) and is entered from Work Order
// Workspace's "Open PM Workspace" action, not browsed to directly.
const PAGES = {
  dashboard: ExecutiveDashboard,
  equipment: Equipment,
  pump: Pump,
  workorder: WorkOrder,
  pm: PM,
  cm: CM,
  cmon: ConditionMonitoring,
  "cmon-workspace": ConditionMonitoringWorkspace,
  history: MaintenanceHistory,
  "pm-workspace": PMWorkOrderWorkspace,
  reports: ReportsWorkspace,
  analytics: AnalyticsWorkspace,
};

export default function LTSAWorkspace({ initialActiveKey = "dashboard" }) {
  const [activeKey, setActiveKey] = useState(initialActiveKey);
  const [navContext, setNavContext] = useState(null);
  const ActivePage = PAGES[activeKey];

  // Extended under APP-ASSET360-001 (per ADR-ASSET360-001) with an
  // optional payload -- { assetTag, selectId } -- carrying cross-domain
  // navigation context (e.g. "jump to Asset 360 already scoped to this
  // pump", or "jump to Work Order already scoped to this record"). Every
  // pre-existing onNavigate(key) call site keeps working unchanged;
  // `context` is a new, optional second argument, not a breaking change
  // to the callback's shape.
  function handleNavigate(key, context) {
    setActiveKey(key);
    setNavContext(context ?? null);
  }

  return (
    <div>
      <div className="no-print">
        <Tabs items={TABS} activeKey={activeKey} onChange={handleNavigate} />
      </div>

      <div className="ltsa-workspace-content">
        <ActivePage onNavigate={handleNavigate} navContext={navContext} />
      </div>
    </div>
  );
}
