import { useEffect, useState } from "react";
import { createLiveStreamClient } from "../api/liveStreamClient";

function LiveOrganizationTree() {
  const [organization, setOrganization] = useState({
    departments: [],
    workers: [],
  });

  useEffect(() => {
    let client;

    try {
      client = createLiveStreamClient({
        onEvent: (event) => {
          if (event.event_type === "ORGANIZATION_SNAPSHOT") {
            setOrganization({
              departments: event.departments || [],
              workers: event.workers || [],
            });
          }
        },
      });
    } catch {
      setOrganization({
        departments: [],
        workers: [],
      });
    }

    return () => {
      if (client) {
        client.close();
      }
    };
  }, []);

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
