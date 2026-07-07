import { useLiveStream } from "../context/LiveStreamContext";

function LiveReasoningStream() {
  const { events } = useLiveStream();

  const steps = events
    .filter((event) => event.event_type === "REASONING_EVENT")
    .slice(0, 30)
    .map((event) => ({
      stage: event.stage || "UNKNOWN",
      summary: event.summary || "",
      timestamp: event.timestamp || new Date().toISOString(),
    }));

  return (
    <section className="panel">
      <h2>Live Reasoning Stream</h2>

      {steps.length === 0 ? (
        <p>No reasoning activity yet.</p>
      ) : (
        <ul>
          {steps.map((step, index) => (
            <li key={index}>
              <strong>{step.stage}</strong>
              <br />
              <span>{step.summary}</span>
              <br />
              <small>{step.timestamp}</small>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default LiveReasoningStream;
