import { Tabs } from "../design-system";
import LTSAAuthGate from "../modules/ltsa/pages/LTSAAuthGate";
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
    // MWO-LTSA-STANDALONE-PRODUCT-SHELL-001 -- LTSA is a standalone
    // product (ApplicationDescriptor.standalone): it must render without
    // Studio's own ProductChrome (platform tab switcher), since LTSA owns
    // its own auth gate and identity chrome (LTSAAuthGate/IdentityBar).
    return (
      <LTSAAuthGate
        organizationContext={organizationContext}
        platformContext={platformContext}
      />
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
