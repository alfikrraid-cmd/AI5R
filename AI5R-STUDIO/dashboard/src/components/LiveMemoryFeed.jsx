import { useEffect, useState } from "react";
import { createLiveStreamClient } from "../api/liveStreamClient";

function LiveMemoryFeed() {
  const [memories, setMemories] = useState([]);

  useEffect(() => {
    let client;

    try {
      client = createLiveStreamClient({
        onEvent: (event) => {
          if (event.event_type === "MEMORY_EVENT") {
            setMemories((current) => [
              {
                memory_id: event.memory_id,
                memory_type: event.memory_type || "MEMORY",
                summary: event.summary || event.content || "Memory captured",
                timestamp: event.timestamp || new Date().toISOString(),
              },
              ...current,
            ].slice(0, 20));
          }
        },
      });
    } catch {
      setMemories([]);
    }

    return () => {
      if (client) {
        client.close();
      }
    };
  }, []);

  return (
    <section className="panel">
      <h2>Live Memory Feed</h2>

      {memories.length === 0 ? (
        <p>No memory events received yet.</p>
      ) : (
        <ul>
          {memories.map((memory, index) => (
            <li key={`${memory.memory_id || "memory"}-${index}`}>
              <strong>{memory.memory_type}</strong>
              <br />
              <span>{memory.summary}</span>
              <br />
              <small>{memory.timestamp}</small>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default LiveMemoryFeed;
