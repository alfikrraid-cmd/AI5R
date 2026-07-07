import { useLiveStream } from "../context/LiveStreamContext";

function LiveRuntimeStatus() {
  const { events, status } = useLiveStream();
  const lastEvent = events[0] || null;
  const heartbeat = lastEvent?.timestamp || null;

  return (
    <section className="panel">
      <h2>Live Runtime Status</h2>

      <div className="runtime-status-grid">
        <div>
          <strong>Connection</strong>
          <p>{status}</p>
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
