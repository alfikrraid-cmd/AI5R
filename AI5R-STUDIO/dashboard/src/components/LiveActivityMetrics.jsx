import { useEffect, useState } from "react";
import { createLiveStreamClient } from "../api/liveStreamClient";

const DEFAULT_METRICS = {
  events: 0,
  tasks: 0,
  memories: 0,
  reasoning: 0,
  workers: 0,
};

function LiveActivityMetrics() {
  const [metrics, setMetrics] = useState(DEFAULT_METRICS);

  useEffect(() => {
    let client;

    try {
      client = createLiveStreamClient({
        onEvent: (event) => {
          setMetrics((current) => {
            const next = { ...current };

            next.events += 1;

            switch (event.event_type) {
              case "TASK_EVENT":
                next.tasks += 1;
                break;

              case "MEMORY_EVENT":
                next.memories += 1;
                break;

              case "REASONING_EVENT":
                next.reasoning += 1;
                break;

              case "ORGANIZATION_SNAPSHOT":
                next.workers =
                  event.workers?.length ??
                  next.workers;
                break;

              default:
                break;
            }

            return next;
          });
        },
      });
    } catch {}

    return () => client?.close();
  }, []);

  return (
    <section className="panel">
      <h2>Live Activity Metrics</h2>

      <table>
        <tbody>
          <tr>
            <td>Total Events</td>
            <td>{metrics.events}</td>
          </tr>

          <tr>
            <td>Task Events</td>
            <td>{metrics.tasks}</td>
          </tr>

          <tr>
            <td>Memory Events</td>
            <td>{metrics.memories}</td>
          </tr>

          <tr>
            <td>Reasoning Events</td>
            <td>{metrics.reasoning}</td>
          </tr>

          <tr>
            <td>Active Workers</td>
            <td>{metrics.workers}</td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}

export default LiveActivityMetrics;
