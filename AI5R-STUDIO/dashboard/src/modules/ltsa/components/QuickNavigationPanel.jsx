import { Button, Card } from "../../../design-system";
import spacing from "../../../design-system/theme/spacing";
import { useOptionalAuth } from "../auth/AuthContext";
import { visibleTabKeys } from "../auth/permissions";

// RC-002 (Executive Dashboard React Implementation): extended with
// Mechanical Seal and Condition Monitoring (both live workspaces added to
// LTSAWorkspace since this panel's original 7 destinations were written).
// "Failure" (per the mission's Workspace Navigation list) is reached via
// the existing "Open Corrective Maintenance" destination below, unchanged
// -- Failure Analysis records are Corrective Maintenance reports (per
// FailureAnalysisWorkspace's own getCMReports() source), not a separate
// registry, so no new "Failure" entry is added to avoid a second,
// competing entry point.
//
// LTSA_MECHANICAL_SEAL_UNIFIED_NAVIGATION_FIX_R1 -- the separate
// "inventory" destination ("Open Mechanical Seal Stock") is removed:
// complete-seal stock now lives inside the unified Mechanical Seal
// workspace, reached by "Open Mechanical Seal" below. The legacy
// "inventory" key/URL still resolves to that workspace (LTSAWorkspace /
// WorkspaceRegistry alias). Entries carry no per-entry permission; the
// whole list is filtered by session capability in usePermittedDestinations
// below (LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B).
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
];

// LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B -- destinations are now
// capability-filtered: only keys the signed-in session may open
// (visibleTabKeys, the same source as the sidebar) are offered, so e.g. a
// PERTAMINA_ENGINEER on the dashboard is never offered "Open Analytics".
// With no AuthProvider (isolated component tests) the full list is kept;
// LTSAWorkspace's own key guard and the backend still apply regardless.
export function usePermittedDestinations() {
  const session = useOptionalAuth()?.session;
  if (!session) return DESTINATIONS;
  const allowed = visibleTabKeys(session);
  return DESTINATIONS.filter((destination) => allowed.includes(destination.key));
}

// MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- retitled "Quick Actions" (was
// "Quick Navigation") per this MWO's "secondary Quick Actions" placement.
export default function QuickNavigationPanel({ onNavigate }) {
  const destinations = usePermittedDestinations();
  return (
    <Card title="Quick Actions">
      <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.sm }}>
        {destinations.map((destination) => (
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
