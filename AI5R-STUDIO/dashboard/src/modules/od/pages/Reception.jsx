import { Button, Card } from "../../../design-system";
import "./Reception.css";

/**
 * The Reception layout (per AI5R-STUDIO/design/layouts.md) — the entry
 * point of Open Design. Orientation only, per philosophy.md: "the interface
 * should feel like entering the headquarters of your own company." No
 * form, no decisions yet.
 */
export default function Reception({ onEnter }) {
  return (
    <div className="od-reception">
      <Card>
        <h1 style={{ marginTop: 0 }}>Welcome to your AI Company</h1>
        <p>
          You're about to describe what you need. We'll turn it into a Business Blueprint your
          company can act on.
        </p>
        <Button onClick={onEnter}>Begin Open Design</Button>
      </Card>
    </div>
  );
}
