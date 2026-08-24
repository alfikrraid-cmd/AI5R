import { Button, Card } from "../../../design-system";
import spacing from "../../../design-system/theme/spacing";

// RC-002 (Executive Dashboard React Implementation): extended with
// Mechanical Seal and Condition Monitoring (both live workspaces added to
// LTSAWorkspace since this panel's original 7 destinations were written)
// and disabled placeholder entries for Drawing/Document/Inventory, which
// have no page yet (per the mission's STOP rule: those three are
// explicitly not implemented by this RC). "Failure" (per the mission's
// Workspace Navigation list) is reached via the existing "Open Corrective
// Maintenance" destination below, unchanged -- Failure Analysis records
// are Corrective Maintenance reports (per FailureAnalysisWorkspace's own
// getCMReports() source), not a separate registry, so no new "Failure"
// entry is added to avoid a second, competing entry point.
//
// Exported (not just default-exported as a component) so DashboardTopBar's
// Workspace Selector can reuse this exact same list instead of maintaining
// a second, independently-authored destination list.
export const DESTINATIONS = [
  { key: "pump", label: "Open Pump Registry" },
  { key: "seal", label: "Open Mechanical Seal" },
  { key: "workorder", label: "Open Work Orders" },
  { key: "pm", label: "Open Preventive Maintenance" },
  { key: "cm", label: "Open Corrective Maintenance" },
  { key: "cmon", label: "Open Condition Monitoring" },
  { key: "history", label: "Open Asset 360" },
  { key: "reports", label: "Open Reports" },
  { key: "analytics", label: "Open Analytics" },
  { key: "drawing", label: "Open Drawing" },
  { key: "document", label: "Open Document" },
  { key: "inventory", label: "Open Inventory", disabled: true },
];

// MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- retitled "Quick Actions" (was
// "Quick Navigation") per this MWO's "secondary Quick Actions" placement;
// DESTINATIONS/onNavigate/every other behavior below is unchanged.
export default function QuickNavigationPanel({ onNavigate }) {
  return (
    <Card title="Quick Actions">
      <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.sm }}>
        {DESTINATIONS.map((destination) => (
          <Button
            key={destination.key}
            disabled={destination.disabled}
            onClick={() => onNavigate(destination.key)}
          >
            {destination.label}{destination.disabled ? " (Coming soon)" : ""}
          </Button>
        ))}
      </div>
    </Card>
  );
}
