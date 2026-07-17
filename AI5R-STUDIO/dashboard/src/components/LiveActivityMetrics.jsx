import { useLiveStream } from "../context/LiveStreamContext";
import { Table } from "../design-system";

const DEFAULT_METRICS = {
  events: 0,
  tasks: 0,
  memories: 0,
  reasoning: 0,
  workers: 0,
};

function buildMetrics(events) {
  return events.reduce(
    (metrics, event) => {
      const next = { ...metrics };

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
          next.workers = event.workers?.length ?? next.workers;
          break;

        default:
          break;
      }

      return next;
    },
    { ...DEFAULT_METRICS }
  );
}

function LiveActivityMetrics() {
  const { events } = useLiveStream();
  const metrics = buildMetrics(events);

  return (
    <section className="panel">
      <h2>Live Activity Metrics</h2>

      <Table
        rows={[
          { label: "Total Events", value: metrics.events },
          { label: "Task Events", value: metrics.tasks },
          { label: "Memory Events", value: metrics.memories },
          { label: "Reasoning Events", value: metrics.reasoning },
          { label: "Active Workers", value: metrics.workers },
        ]}
      />
    </section>
  );
}

export { buildMetrics };
export default LiveActivityMetrics;
