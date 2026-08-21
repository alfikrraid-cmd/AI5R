import { Button, Tabs } from "../design-system";
import { usePlatformContext } from "./PlatformContext";

function platformTabs(applications) {
  return applications.map((application) => ({
    key: application.applicationId,
    label: application.displayName === "AI5ROS" ? "AI5ROS" : application.displayName,
  }));
}

function statusLabel(status) {
  return status === "active" ? "Available" : "Unavailable";
}

export default function Landing({ onNavigateApplication }) {
  const { applications } = usePlatformContext();
  const productApplications = applications.filter((application) => application.applicationId !== "platform-home");

  return (
    <div className="dashboard">
      <h1>AI5ROS</h1>

      <div className="dashboard-nav">
        <Tabs items={platformTabs(applications)} activeKey="platform-home" onChange={onNavigateApplication} />
      </div>

      <section className="grid" aria-label="Available Applications">
        {productApplications.map((application) => {
          const isAvailable = application.status === "active";

          return (
            // MWO-LTSA-DEMO-READINESS-CLOSURE-001 -- was "metric-card", a
            // class never defined anywhere in this codebase, leaving these
            // cards completely unstyled (no panel background, no padding,
            // no border-radius -- root cause of the "pale/washed out,
            // barely readable" Control Tower symptom). ".card" is the
            // pre-existing, already-styled class index.css defines for
            // exactly this purpose (colors.js's own header comment: "match
            // ... src/index.css body/.card exactly"). The "Open" button is
            // likewise switched from a bare unstyled <button> to the
            // existing design-system Button (colors.info background,
            // colors.text foreground) -- both are restorations of already-
            // intended styling, not new design.
            <article className="card" key={application.applicationId}>
              <h3>{application.displayName}</h3>
              <p>{statusLabel(application.status)}</p>
              <Button
                disabled={!isAvailable}
                onClick={() => onNavigateApplication(application.applicationId)}
              >
                Open
              </Button>
            </article>
          );
        })}
      </section>
    </div>
  );
}
