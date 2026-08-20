import { EmptySection } from "./KnowledgeCard";

// MWO-LTSA-032A -- KnowledgeInventory: Inventory body (KnowledgeCard
// variant="row-list"). item.level is "ok" | "low" | "out" per the Open
// Design's own InvItem type -- which has no "unknown" case, even though
// the real backend can legitimately return a null quantity_on_hand (no
// stock record yet, per get_pump_spare_parts's own "unknown vs confirmed
// zero" discipline). This is a disclosed Open Design gap, not silently
// resolved here: unknown-quantity rows are mapped to level="low" (the
// least misleading of the three available choices) by useKnowledgeWorkspace,
// with the qty text itself saying "Unknown" -- see the deliverable report.
export default function KnowledgeInventory({ items = [] }) {
  if (!items.length) {
    return <EmptySection title="Belum ada data inventaris" />;
  }

  return (
    <div data-testid="knowledge-inventory">
      {items.map((item) => (
        <div className="inv-row" key={item.id}>
          <span className="inv-name">
            <span className={`inv-dot ${item.level}`} />
            {item.name}
          </span>
          <span className="inv-avail">{item.qty}</span>
          <span className="inv-meta">{item.meta}</span>
        </div>
      ))}
    </div>
  );
}
