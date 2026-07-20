import { useState } from "react";
import { Tabs } from "../../../design-system";
import Pump from "./Pump";
import WorkOrder from "./WorkOrder";
import PM from "./PM";
import CM from "./CM";
import "./LTSAWorkspace.css";

const TABS = [
  { key: "pump", label: "Pump" },
  { key: "workorder", label: "Work Order" },
  { key: "pm", label: "Preventive Maintenance" },
  { key: "cm", label: "Corrective Maintenance" },
];

const PAGES = {
  pump: Pump,
  workorder: WorkOrder,
  pm: PM,
  cm: CM,
};

export default function LTSAWorkspace() {
  const [activeKey, setActiveKey] = useState("pump");
  const ActivePage = PAGES[activeKey];

  return (
    <div>
      <Tabs items={TABS} activeKey={activeKey} onChange={setActiveKey} />

      <div className="ltsa-workspace-content">
        <ActivePage />
      </div>
    </div>
  );
}
