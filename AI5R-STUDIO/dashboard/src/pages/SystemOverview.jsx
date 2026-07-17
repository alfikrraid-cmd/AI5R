import { useEffect, useState } from "react";
import { MetricCard } from "../design-system";

export default function SystemOverview() {
  const [status, setStatus] = useState({
    factory: "GREEN",
    stations: 12,
    running: 3,
    queue: 1
  });

  useEffect(() => {
    const t = setInterval(() => {
      setStatus(s => ({
        ...s,
        running: Math.floor(Math.random() * 5),
        queue: Math.floor(Math.random() * 3)
      }));
    }, 2000);

    return () => clearInterval(t);
  }, []);

  return (
    <div>
      <h1>System Overview</h1>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <MetricCard title="Factory" value={status.factory} />
        <MetricCard title="Stations" value={status.stations} />
        <MetricCard title="Running" value={status.running} />
        <MetricCard title="Queue" value={status.queue} />
      </div>
    </div>
  );
}
