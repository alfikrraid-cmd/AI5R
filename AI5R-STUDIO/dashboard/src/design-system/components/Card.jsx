import Panel from "./Panel";

export default function Card({ title, children }) {
  return (
    <Panel>
      {title ? <h2>{title}</h2> : null}
      {children}
    </Panel>
  );
}
