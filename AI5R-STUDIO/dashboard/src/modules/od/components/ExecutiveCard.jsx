import { Badge, Panel } from "../../../design-system";

/**
 * One executive, shown as present and available — per OD-002's empty-state
 * guidance, an idle executive still reads as alive, never grayed out or
 * hidden. `showGreeting` renders the once-only first-time introduction
 * (OD-002 "First-Time Executive Experience"); omitted on later visits.
 */
export default function ExecutiveCard({ executive, showGreeting = false }) {
  return (
    <Panel>
      <h3 style={{ margin: 0 }}>{executive.name}</h3>
      <p style={{ margin: "4px 0" }}>{executive.role}</p>
      <Badge variant="success">Available</Badge>

      {showGreeting ? (
        <p data-testid="executive-greeting" style={{ marginTop: 8 }}>
          {executive.greeting}
        </p>
      ) : null}
    </Panel>
  );
}
