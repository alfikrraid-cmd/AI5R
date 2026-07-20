import { Button, Card } from "../../../design-system";
import spacing from "../../../design-system/theme/spacing";

const DESTINATIONS = [
  { key: "pump", label: "Open Pump Registry" },
  { key: "workorder", label: "Open Work Orders" },
  { key: "pm", label: "Open Preventive Maintenance" },
  { key: "cm", label: "Open Corrective Maintenance" },
  { key: "history", label: "Open Asset 360" },
];

export default function QuickNavigationPanel({ onNavigate }) {
  return (
    <Card title="Quick Navigation">
      <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.sm }}>
        {DESTINATIONS.map((destination) => (
          <Button key={destination.key} onClick={() => onNavigate(destination.key)}>
            {destination.label}
          </Button>
        ))}
      </div>
    </Card>
  );
}
