import { useEffect, useState } from "react";
import { createLiveStreamClient } from "../api/liveStreamClient";

function LiveTaskTimeline() {
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    let client;

    try {
      client = createLiveStreamClient({
        onEvent: (event) => {
          if (event.event_type === "TASK_EVENT") {
            setTasks((current) => [
              {
                task_id: event.task_id,
                title: event.title || event.task_name || "Untitled Task",
                status: event.status || "UNKNOWN",
                timestamp: event.timestamp || new Date().toISOString(),
              },
              ...current,
            ].slice(0, 20));
          }
        },
      });
    } catch {
      setTasks([]);
    }

    return () => {
      if (client) {
        client.close();
      }
    };
  }, []);

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
