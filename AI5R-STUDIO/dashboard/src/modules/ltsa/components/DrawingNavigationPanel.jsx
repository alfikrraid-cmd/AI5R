import { Button, Card, EmptyState } from "../../../design-system";
import spacing from "../../../design-system/theme/spacing";

/**
 * "Navigate to related workspace" (RC-003A objective). Reuses the same
 * onNavigate(key, context) contract already used by every other
 * cross-workspace deep link in LTSA (e.g. Pump.jsx's
 * onNavigate("history", { assetTag })) -- not a new navigation mechanism.
 * Inventory has no page yet and renders disabled, matching
 * QuickNavigationPanel's established disabled-placeholder pattern.
 *
 * MWO-LTSA-062 -- Document enabled: DocumentWorkspace.jsx now consumes
 * navContext.assetTag (previously it had a page but this button was still
 * disabled, a real navigation gap this MWO's "Document/Drawing navigation
 * works" requirement closes) -- same real onNavigate("document",
 * { assetTag }) call every other enabled destination here already sends.
 */
export default function DrawingNavigationPanel({ drawing, onNavigate }) {
  if (!drawing) {
    return (
      <Card title="Related Workspaces">
        <EmptyState
          title="No related workspaces to show"
          description="Open a drawing to see where it connects."
        />
      </Card>
    );
  }

  const context = { assetTag: drawing.equipmentTag };

  const destinations = [
    { key: "pump", label: "Open Pump", context },
    { key: "seal", label: "Open Mechanical Seal", context },
    { key: "document", label: "Open Document", context },
    { key: "pm", label: "Open Preventive Maintenance", context },
    { key: "cmon", label: "Open Condition Monitoring", context },
    { key: "cm", label: "Open Failure Records", context },
    { key: "workorder", label: "Open Work Orders", context },
    { key: "inventory", label: "Open Inventory", disabled: true },
    { key: "dashboard", label: "Open Dashboard" },
  ];

  return (
    <Card title="Related Workspaces">
      <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.sm }}>
        {destinations.map((destination) => (
          <Button
            key={destination.key}
            disabled={destination.disabled}
            onClick={() => onNavigate(destination.key, destination.context)}
          >
            {destination.label}{destination.disabled ? " (Coming soon)" : ""}
          </Button>
        ))}
      </div>
    </Card>
  );
}
