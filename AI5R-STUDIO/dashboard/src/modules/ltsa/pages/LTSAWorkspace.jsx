import { useState } from "react";
import { Tabs } from "../../../design-system";
import ExecutiveDashboard from "./ExecutiveDashboard";
import Pump from "./Pump";
import WorkOrder from "./WorkOrder";
import PM from "./PM";
import CM from "./CM";
import MaintenanceHistory from "./MaintenanceHistory";
import "./LTSAWorkspace.css";

const TABS = [
  { key: "dashboard", label: "Executive Dashboard" },
  { key: "pump", label: "Pump" },
  { key: "workorder", label: "Work Order" },
  { key: "pm", label: "Preventive Maintenance" },
  { key: "cm", label: "Corrective Maintenance" },
  { key: "history", label: "Maintenance History" },
];

const PAGES = {
  dashboard: ExecutiveDashboard,
  pump: Pump,
  workorder: WorkOrder,
  pm: PM,
  cm: CM,
  history: MaintenanceHistory,
};

export default function LTSAWorkspace() {
  const [activeKey, setActiveKey] = useState("dashboard");
  const ActivePage = PAGES[activeKey];

  return (
    <div>
      <Tabs items={TABS} activeKey={activeKey} onChange={setActiveKey} />

      <div className="ltsa-workspace-content">
        <ActivePage onNavigate={setActiveKey} />
      </div>
    </div>
  );
}
