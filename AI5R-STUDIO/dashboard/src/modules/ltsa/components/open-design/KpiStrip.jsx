/**
 * UI-D2A -- bounded shared primitive, first consumer is the Work Order
 * Workspace. Deliberately generic (label/value/tone only, no domain
 * knowledge) so it is directly reusable by a future PM/Condition
 * Monitoring/Failure Analysis/Inventory rebuild without modification --
 * per this MWO's own scope boundary, none of those pages are refactored
 * to use it yet. Styled via `.kpi-strip`/`.kpi-strip-card` in the shared
 * LTSAOpenDesign.css, using the same --surface/--border/--fg/--muted/
 * --status-* tokens every other Open Design component already reads from
 * its `.ltsa-open-design` ancestor -- no new color system.
 *
 * Data discipline: this component never computes or fabricates a value.
 * Every item's `value` must already be a real, honestly-derived string
 * (a real count, a real aggregate, or "N/A") -- callers own that
 * derivation entirely.
 */
export default function KpiStrip({ items }) {
  return (
    <div className="kpi-strip">
      {items.map((item) => (
        <div className="kpi-strip-card" key={item.label}>
          <span className="kpi-strip-label">{item.label}</span>
          <strong className={`kpi-strip-value${item.tone ? ` tone-${item.tone}` : ""}`}>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}
