import { useLiveStream } from "../context/LiveStreamContext";

function LiveOrganizationTree() {
  const { events } = useLiveStream();

  const snapshot = events.find(
    (event) => event.event_type === "ORGANIZATION_SNAPSHOT"
  );

  const organization = {
    departments: snapshot?.departments || [],
    workers: snapshot?.workers || [],
  };

  return (
    <section className="panel">
      <h2>Live Organization Tree</h2>

      <div>
        <strong>Departments</strong>
        {organization.departments.length === 0 ? (
          <p>No departments reported yet.</p>
        ) : (
          <ul>
            {organization.departments.map((department) => (
              <li key={department.department_id || department.name}>
                {department.name || department.department_id}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <strong>Workers</strong>
        {organization.workers.length === 0 ? (
          <p>No workers reported yet.</p>
        ) : (
          <ul>
            {organization.workers.map((worker) => (
              <li key={worker.worker_id || worker.name}>
                {worker.name || worker.worker_id} — {worker.status || "UNKNOWN"}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

export default LiveOrganizationTree;
