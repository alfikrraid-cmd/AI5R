import Panel from "./Panel";

export default function MetricCard({ title, value }) {
  return (
    <Panel>
      <h3>{title}</h3>
      <strong>{value}</strong>
    </Panel>
  );
}
