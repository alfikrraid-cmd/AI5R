import { useEffect, useState } from "react";

import { getDashboardData, getSystemStatus } from "../api/ai5rClient";
import AgentPanel from "../components/AgentPanel";
import BrainActivity from "../components/BrainActivity";
import BrainEventStream from "../components/BrainEventStream";
import BrainStream from "../components/BrainStream";
import CommandConsole from "../components/CommandConsole";
import EmployeePanel from "../components/EmployeePanel";
import IntelligenceGraph from "../components/IntelligenceGraph";
import LiveActivityMetrics from "../components/LiveActivityMetrics";
import LiveEventStream from "../components/LiveEventStream";
import LiveMemoryFeed from "../components/LiveMemoryFeed";
import LiveOrganizationTree from "../components/LiveOrganizationTree";
import LiveReasoningStream from "../components/LiveReasoningStream";
import LiveRuntimeStatus from "../components/LiveRuntimeStatus";
import LiveTaskTimeline from "../components/LiveTaskTimeline";
import MemoryPanel from "../components/MemoryPanel";
import { MetricCard, Tabs, Timeline } from "../design-system";
import LTSAWorkspace from "../modules/ltsa/pages/LTSAWorkspace";
import PMWorkspace from "../modules/ltsa/pages/PMWorkspace";
import ODWorkspace from "../modules/od/pages/ODWorkspace";
import { UMKMAgents, UMKMInsight, UMKMOverview } from "../products/UMKM_OS";
import AdvisorChat from "../products/UMKM_OS/components/AdvisorChat";
import ExecutiveDashboard from "../products/UMKM_OS/components/ExecutiveDashboard";
import UMKMLiveStatus from "../products/UMKM_OS/components/UMKMLiveStatus";

export const PUMP_WORKSPACE_ROUTE = "/ltsa/pump-workspace";
export const PM_WORKSPACE_ROUTE = "/ltsa/pm-workspace";

function platformTabs(applications) {
  return applications.map((application) => ({
    key: application.applicationId,
    label: application.displayName === "AI5ROS" ? "OS Command Center" : application.displayName,
  }));
}

function PlatformHome({ applications, onNavigateApplication }) {
  const [system, setSystem] = useState({ status: "LOADING" });
  const [dashboard, setDashboard] = useState({ agents: 0, memories: 0 });

  useEffect(() => {
    getSystemStatus().then((data) => setSystem(data));
    getDashboardData().then((data) => setDashboard(data));
  }, []);

  return (
    <div className="dashboard">
      <h1>AI5R OS COMMAND CENTER</h1>

      <div className="dashboard-nav">
        <Tabs items={platformTabs(applications)} activeKey="platform-home" onChange={onNavigateApplication} />
      </div>

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
    </div>
  );
}

function ProductChrome({ activeKey, applications, onNavigateApplication, children }) {
  return (
    <div className="dashboard">
      <h1>AI5R OS COMMAND CENTER</h1>
      <div className="dashboard-nav">
        <Tabs items={platformTabs(applications)} activeKey={activeKey} onChange={onNavigateApplication} />
      </div>
      {children}
    </div>
  );
}

export default function ApplicationAdapter({ application, applications, onNavigateApplication }) {
  if (application?.applicationId === "ltsa") {
    return (
      <ProductChrome activeKey="ltsa" applications={applications} onNavigateApplication={onNavigateApplication}>
        {window.location.pathname === PM_WORKSPACE_ROUTE ? <PMWorkspace /> : <LTSAWorkspace initialActiveKey="history" />}
      </ProductChrome>
    );
  }

  if (application?.applicationId === "od") {
    return (
      <ProductChrome activeKey="od" applications={applications} onNavigateApplication={onNavigateApplication}>
        <ODWorkspace />
      </ProductChrome>
    );
  }

  return <PlatformHome applications={applications} onNavigateApplication={onNavigateApplication} />;
}
