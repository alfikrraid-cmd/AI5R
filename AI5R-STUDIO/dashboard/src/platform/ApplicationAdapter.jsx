import { Tabs } from "../design-system";
import LTSAWorkspace from "../modules/ltsa/pages/LTSAWorkspace";
import ODWorkspace from "../modules/od/pages/ODWorkspace";
import Landing from "./Landing";

export const PUMP_WORKSPACE_ROUTE = "/ltsa/pump-workspace";
export const PM_WORKSPACE_ROUTE = "/ltsa/pm-workspace";

function platformTabs(applications) {
  return applications.map((application) => ({
    key: application.applicationId,
    label: application.displayName,
  }));
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

export default function ApplicationAdapter({
  application,
  applications,
  onNavigateApplication,
  organizationContext,
  platformContext,
}) {
  if (application?.applicationId === "ltsa") {
    return (
      <ProductChrome activeKey="ltsa" applications={applications} onNavigateApplication={onNavigateApplication}>
        <LTSAWorkspace
          initialActiveKey="history"
          organizationContext={organizationContext}
          platformContext={platformContext}
        />
      </ProductChrome>
    );
  }

  if (application?.applicationId === "od") {
    return (
      <ProductChrome activeKey="od" applications={applications} onNavigateApplication={onNavigateApplication}>
        <ODWorkspace organizationContext={organizationContext} platformContext={platformContext} />
      </ProductChrome>
    );
  }

  return <Landing onNavigateApplication={onNavigateApplication} />;
}
