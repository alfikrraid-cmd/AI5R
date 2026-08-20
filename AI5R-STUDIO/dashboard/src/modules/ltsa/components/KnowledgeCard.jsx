// MWO-LTSA-032A -- KnowledgeCard: one shell, four variants (grid | kv |
// row-list | prose), per the approved Open Design
// (DESIGN/LTSA/KNOWLEDGE_PANEL/knowledge-panel-spec.md §1/§8 D9). Shell
// values (.kn-card) are the exact border/radius/background the wireframe
// ported from .eng-summary-card/.eng-insight-card -- nothing new here.
export default function KnowledgeCard({ variant, locked = false, children }) {
  const classes = ["kn-card", locked ? "locked" : ""].filter(Boolean).join(" ");

  return (
    <div className={classes} data-variant={variant} data-testid="knowledge-card">
      {children}
    </div>
  );
}

// Shared per-section empty state (.eng-empty), per spec §6 States matrix:
// "Each section independently renders .eng-empty (compact) when its
// array/object is empty/undefined." Reused by every domain component
// below rather than each defining its own empty markup.
export function EmptySection({ title, description, compact = true, error = false }) {
  const classes = ["eng-empty", compact ? "compact" : "", error ? "is-error" : ""].filter(Boolean).join(" ");

  return (
    <div className={classes}>
      <h4>{title}</h4>
      {description ? <p>{description}</p> : null}
    </div>
  );
}
