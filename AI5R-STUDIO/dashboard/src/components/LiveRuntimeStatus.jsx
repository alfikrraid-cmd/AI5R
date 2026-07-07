import { useEffect, useState } from "react";
import { createLiveStreamClient } from "../api/liveStreamClient";

function LiveRuntimeStatus() {
  const [connection, setConnection] = useState("CONNECTING");
  const [lastEvent, setLastEvent] = useState(null);
  const [heartbeat, setHeartbeat] = useState(null);

  useEffect(() => {
    let client;

    try {
      client = createLiveStreamClient({
        onEvent: (event) => {
          setConnection("LIVE");
          setLastEvent(event);
          setHeartbeat(new Date().toISOString());
        },
        onError: () => {
          setConnection("RECONNECTING");
        },
      });
    } catch {
      setConnection("UNAVAILABLE");
    }

    return () => {
      if (client) {
        client.close();
      }
    };
  }, []);

  return (
    <section className="panel">
      <h2>Live Runtime Status</h2>

      <div className="runtime-status-grid">
        <div>
          <strong>Connection</strong>
          <p>{connection}</p>
        </div>

        <div>
          <strong>Last Heartbeat</strong>
          <p>{heartbeat || "Waiting for runtime event..."}</p>
        </div>

        <div>
          <strong>Last Event</strong>
          <p>{lastEvent?.event_type || "No event received yet"}</p>
        </div>
      </div>
    </section>
  );
}

export default LiveRuntimeStatus;
