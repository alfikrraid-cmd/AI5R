import { Button, Card } from "../../../design-system";

/**
 * A small, fixed set of next actions for a freshly-sealed workspace — per
 * OD-002, exactly three, not a menu, each routing to one of the other
 * Headquarters tabs via the same onNavigate threading LTSAWorkspace uses.
 */
export default function SuggestedActionsPanel({ onNavigate }) {
  return (
    <Card title="Suggested Next Actions">
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Button onClick={() => onNavigate("studio")}>Bring your first ask to the company</Button>
        <Button onClick={() => onNavigate("meeting")}>Meet your executives</Button>
        <Button onClick={() => onNavigate("presentation")}>Review your Business Blueprint</Button>
      </div>
    </Card>
  );
}
