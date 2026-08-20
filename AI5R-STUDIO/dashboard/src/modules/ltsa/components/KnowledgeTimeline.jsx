import { EmptySection } from "./KnowledgeCard";

// MWO-LTSA-032A -- KnowledgeTimeline: Equipment Timeline. Explicitly
// exempt from KnowledgeCard (spec §1 "Explicitly out of scope" / §8 D9)
// -- .timeline has no bordered shell anywhere in the real, shipped
// MaintenanceHistory.css, so this renders unwrapped, exactly as reused.
const TAG_LABELS = { pm: "PM", cm: "CM", breakdown: "Breakdown", wo: "WO" };

export default function KnowledgeTimeline({ items = [] }) {
  if (!items.length) {
    return (
      <EmptySection
        title="Belum ada riwayat"
        description="Belum ada peristiwa tercatat untuk peralatan ini."
      />
    );
  }

  return (
    <ol className="timeline" data-testid="knowledge-timeline">
      {items.map((item) => (
        <li className="t-item" key={item.id}>
          <span className="t-dot" aria-hidden="true" />
          <div className="t-row">
            <span className="t-title">
              <span className={`t-tag ${item.kind}`}>{TAG_LABELS[item.kind] ?? item.kind}</span>
              {item.title}
            </span>
            <span className="t-time">{item.time}</span>
          </div>
          {item.desc ? <p className="t-desc">{item.desc}</p> : null}
        </li>
      ))}
    </ol>
  );
}
