import { Tabs } from "../design-system";
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
            <article className="metric-card" key={application.applicationId}>
              <h3>{application.displayName}</h3>
              <p>{statusLabel(application.status)}</p>
              <button
                disabled={!isAvailable}
                onClick={() => onNavigateApplication(application.applicationId)}
                type="button"
              >
                Open
              </button>
            </article>
          );
        })}
      </section>
    </div>
  );
}
