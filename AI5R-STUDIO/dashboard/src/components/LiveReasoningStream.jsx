import { useEffect, useState } from "react";
import { createLiveStreamClient } from "../api/liveStreamClient";

function LiveReasoningStream() {
  const [steps, setSteps] = useState([]);

  useEffect(() => {
    let client;

    try {
      client = createLiveStreamClient({
        onEvent: (event) => {
          if (event.event_type === "REASONING_EVENT") {
            setSteps((current) => [
              {
                stage: event.stage || "UNKNOWN",
                summary: event.summary || "",
                timestamp: event.timestamp || new Date().toISOString(),
              },
              ...current,
            ].slice(0, 30));
          }
        },
      });
    } catch {
      setSteps([]);
    }

    return () => client?.close();
  }, []);

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
