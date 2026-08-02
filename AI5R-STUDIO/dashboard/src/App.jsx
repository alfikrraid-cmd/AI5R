import { useEffect, useState } from "react";

import {
    getSystemStatus,
    getDashboardData
} from "./api/ai5rClient";

import { LiveStreamProvider } from "./context/LiveStreamContext";

import { MetricCard, Tabs, Timeline } from "./design-system";
import AgentPanel from "./components/AgentPanel";
import BrainActivity from "./components/BrainActivity";
import MemoryPanel from "./components/MemoryPanel";
import BrainStream from "./components/BrainStream";
import LiveEventStream from "./components/LiveEventStream";
import LiveRuntimeStatus from "./components/LiveRuntimeStatus";
import LiveOrganizationTree from "./components/LiveOrganizationTree";
import LiveTaskTimeline from "./components/LiveTaskTimeline";
import LiveMemoryFeed from "./components/LiveMemoryFeed";
import LiveReasoningStream from "./components/LiveReasoningStream";
import LiveActivityMetrics from "./components/LiveActivityMetrics";
import BrainEventStream from "./components/BrainEventStream";
import EmployeePanel from "./components/EmployeePanel";
import IntelligenceGraph from "./components/IntelligenceGraph";
import CommandConsole from "./components/CommandConsole";
import { UMKMOverview, UMKMAgents, UMKMInsight } from "./products/UMKM_OS";
import UMKMLiveStatus from "./products/UMKM_OS/components/UMKMLiveStatus";
import AdvisorChat from "./products/UMKM_OS/components/AdvisorChat";
import ExecutiveDashboard from "./products/UMKM_OS/components/ExecutiveDashboard";
import LTSAWorkspace from "./modules/ltsa/pages/LTSAWorkspace";

export const PUMP_WORKSPACE_ROUTE = "/ltsa/pump-workspace";

function sectionFromPath(pathname) {
    return pathname === PUMP_WORKSPACE_ROUTE ? "ltsa" : "os";
}

const SECTION_TABS = [
    { key: "os", label: "OS Command Center" },
    { key: "ltsa", label: "LTSA" },
];

function App(){
    const [system,setSystem] = useState({ status:"LOADING" });
    const [dashboard,setDashboard] = useState({ agents:0, memories:0 });
    const [activeSection,setActiveSection] = useState(() => sectionFromPath(window.location.pathname));

    useEffect(()=>{
        getSystemStatus().then(data=>setSystem(data));
        getDashboardData().then(data=>setDashboard(data));
    },[]);

    useEffect(() => {
        const handlePopState = () => setActiveSection(sectionFromPath(window.location.pathname));
        window.addEventListener("popstate", handlePopState);
        return () => window.removeEventListener("popstate", handlePopState);
    }, []);

    function handleSectionChange(section) {
        const route = section === "ltsa" ? PUMP_WORKSPACE_ROUTE : "/";
        window.history.pushState({}, "", route);
        setActiveSection(section);
    }

    return (
        <LiveStreamProvider>
        <div className="dashboard">
            <h1>🌳 AI5R OS COMMAND CENTER</h1>

            <div className="dashboard-nav">
                <Tabs items={SECTION_TABS} activeKey={activeSection} onChange={handleSectionChange} />
            </div>

            {activeSection === "ltsa" ? (
                <LTSAWorkspace initialActiveKey="history" />
            ) : (
            <>
            <div className="grid">
                <MetricCard title="System" value={system.status} />
                <MetricCard title="Service" value={system.service || "-"} />
                <MetricCard title="Agents" value={dashboard.agents} />
                <MetricCard title="Memory" value={dashboard.memories} />
            </div>

            <AgentPanel />
            <BrainActivity />
            <MemoryPanel />
            <BrainStream />

            <LiveRuntimeStatus />
            <LiveOrganizationTree />
            <LiveTaskTimeline />
            <LiveMemoryFeed />
            <LiveReasoningStream />
            <LiveActivityMetrics />
            <LiveEventStream />

            <BrainEventStream />
            <EmployeePanel />
            <Timeline />
            <IntelligenceGraph />
            <CommandConsole />

            <UMKMOverview />
            <UMKMAgents />
            <UMKMInsight />
            <UMKMLiveStatus />
            <AdvisorChat />
            <ExecutiveDashboard />
            </>
            )}
        </div>
        </LiveStreamProvider>
    );
}

export default App;
