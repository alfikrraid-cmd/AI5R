import { Card, EmptyState } from "../../../design-system";

// MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- renders FleetExecutiveSummary's
// own top_risks (GET /api/ltsa/fleet/powerbi, already-computed
// Recommendation-derived entries -- no new derivation here). This panel
// is entirely OPTIONAL-data-driven: summary is null whenever the
// Reliability/Power BI fetch hasn't resolved or failed (per this MWO's
// "optional data must not break core overview" rule) -- shown as an
// explicit "data unavailable" EmptyState, never hidden and never
// backfilled from the bounded overview (which has no per-pump risk data).
export default function AssetsAttentionPanel({ summary }) {
  if (!summary) {
    return (
      <Card title="Assets Needing Attention">
        <EmptyState title="Data unavailable" description="Reliability data did not load for this session." />
      </Card>
    );
  }

  if (!summary.top_risks || summary.top_risks.length === 0) {
    return (
      <Card title="Assets Needing Attention">
        <EmptyState title="No assets flagged" description="No open risk recommendations were found." />
      </Card>
    );
  }

  return (
    <Card title="Assets Needing Attention">
      <ul className="assets-attention-list">
        {summary.top_risks.map((risk) => (
          <li key={`${risk.tag_number}-${risk.rule_code}`} className="assets-attention-row">
            <span className="assets-attention-tag">{risk.tag_number}</span>
            <span className="assets-attention-title">{risk.title}</span>
            <span className="assets-attention-action">{risk.action}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
