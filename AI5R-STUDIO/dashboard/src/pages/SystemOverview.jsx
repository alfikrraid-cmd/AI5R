import { useEffect, useState } from "react";

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
        <Card label="Factory" value={status.factory} />
        <Card label="Stations" value={status.stations} />
        <Card label="Running" value={status.running} />
        <Card label="Queue" value={status.queue} />
      </div>
    </div>
  );
}

function Card({ label, value }) {
  return (
    <div style={{
      background: "white",
      padding: 16,
      borderRadius: 10
    }}>
      <div style={{ fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: "bold" }}>{value}</div>
    </div>
  );
}
