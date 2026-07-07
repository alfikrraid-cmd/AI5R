import { useLiveStream } from "../context/LiveStreamContext";

function LiveTaskTimeline() {
  const { events } = useLiveStream();
  const tasks = events
    .filter((event) => event.event_type === "TASK_EVENT")
    .slice(0, 20)
    .map((event) => ({
      task_id: event.task_id,
      title: event.title || event.task_name || "Untitled Task",
      status: event.status || "UNKNOWN",
      timestamp: event.timestamp || new Date().toISOString(),
    }));

  return (
    <section className="panel">
      <h2>Live Task Timeline</h2>

      {tasks.length === 0 ? (
        <p>No task events received yet.</p>
      ) : (
        <ol>
          {tasks.map((task, index) => (
            <li key={`${task.task_id || "task"}-${index}`}>
              <strong>{task.title}</strong>
              <br />
              <span>{task.status}</span>
              <br />
              <small>{task.timestamp}</small>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default LiveTaskTimeline;
