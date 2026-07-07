import { useLiveStream } from "../context/LiveStreamContext";

function LiveEventStream() {
  const { events, status } = useLiveStream();
  return (
    <section className="panel">
      <h2>Live Event Stream</h2>
      <p>Status: {status}</p>

      <div className="event-stream">
        {events.length === 0 ? (
          <p>No live events yet.</p>
        ) : (
          events.slice(0, 20).map((event, index) => (
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
