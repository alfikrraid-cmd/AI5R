/**
 * Explicit "Coming Soon / Not Yet Available" state for an approved
 * Pump Workspace capability whose backend does not exist yet
 * (AI Assessment, Drawing/P&ID, CM manual submission -- see the
 * Engineering Report). Preserves the approved component/layout slot;
 * never fabricates data in its place.
 */
export default function PumpWorkspaceComingSoon({ label }) {
  return (
    <div className="coming-soon" role="status">
      <span className="coming-soon-badge">Coming Soon</span>
      <p className="coming-soon-text">{label} is not yet available — its backend capability does not exist yet.</p>
    </div>
  );
}
