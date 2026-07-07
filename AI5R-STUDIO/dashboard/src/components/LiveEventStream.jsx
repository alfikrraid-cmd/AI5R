import { useEffect, useState } from "react";
import { createLiveStreamClient } from "../api/liveStreamClient";

function LiveEventStream() {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("CONNECTING");

  useEffect(() => {
    let client;

    try {
      client = createLiveStreamClient({
        onEvent: (event) => {
          setStatus("LIVE");
          setEvents((current) => [event, ...current].slice(0, 20));
        },
        onError: () => {
          setStatus("RECONNECTING");
        },
      });
    } catch {
      setStatus("UNAVAILABLE");
    }

    return () => {
      if (client) {
        client.close();
      }
    };
  }, []);

  return (
    <section className="panel">
      <h2>Live Event Stream</h2>
      <p>Status: {status}</p>

      <div className="event-stream">
        {events.length === 0 ? (
          <p>No live events yet.</p>
        ) : (
          events.map((event, index) => (
            <div className="event-card" key={`${event.event_id || "event"}-${index}`}>
              <strong>{event.event_type || "EVENT"}</strong>
              <pre>{JSON.stringify(event, null, 2)}</pre>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

export default LiveEventStream;
