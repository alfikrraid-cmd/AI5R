import { useState } from "react";
import { Tabs } from "../../../design-system";
import ExecutiveDashboard from "./ExecutiveDashboard";
import Pump from "./Pump";
import WorkOrder from "./WorkOrder";
import PM from "./PM";
import CM from "./CM";
import MaintenanceHistory from "./MaintenanceHistory";
import ReportsWorkspace from "./ReportsWorkspace";
import AnalyticsWorkspace from "./AnalyticsWorkspace";
import "./LTSAWorkspace.css";

const TABS = [
  { key: "dashboard", label: "Executive Dashboard" },
  { key: "pump", label: "Pump" },
  { key: "workorder", label: "Work Order" },
  { key: "pm", label: "Preventive Maintenance" },
  { key: "cm", label: "Corrective Maintenance" },
  { key: "history", label: "Maintenance History" },
  { key: "reports", label: "Reports" },
  { key: "analytics", label: "Analytics" },
];

const PAGES = {
  dashboard: ExecutiveDashboard,
  pump: Pump,
  workorder: WorkOrder,
  pm: PM,
  cm: CM,
  history: MaintenanceHistory,
  reports: ReportsWorkspace,
  analytics: AnalyticsWorkspace,
};

export default function LTSAWorkspace() {
  const [activeKey, setActiveKey] = useState("dashboard");
  const ActivePage = PAGES[activeKey];

  return (
    <div>
      <div className="no-print">
        <Tabs items={TABS} activeKey={activeKey} onChange={setActiveKey} />
      </div>

      <div className="ltsa-workspace-content">
        <ActivePage onNavigate={setActiveKey} />
      </div>
    </div>
  );
}
