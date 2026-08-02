import { useState } from "react";
import { TIMELINE_FILTER_CHIPS } from "../utils/pumpWorkspaceEventTaxonomy";
import { TierIcon } from "./PumpWorkspaceIcons";

/**
 * Vertical dot-list Timeline, ported 1:1 from
 * DESIGN/LTSA/PUMP_WORKSPACE/pump-workspace.html's Timeline component.
 * Items are already mapped to { id, tier, tag, title, date,
 * assignedTechnician } by pumpWorkspaceEventTaxonomy.toWorkspaceTimelineItem
 * -- this component renders only, no data logic.
 */
export default function PumpWorkspaceTimeline({ items }) {
  const [filter, setFilter] = useState("all");

  const shown = filter === "all" ? items : items.filter((item) => item.tier === filter);

  return (
    <section id="timeline-section" data-od-id="timeline-section">
      <div className="section-head">
        <span className="eyebrow">History</span>
        <div className="timeline-filter">
          {TIMELINE_FILTER_CHIPS.map((chip) => (
            <button
              key={chip.id}
              type="button"
              className="tf-chip"
              data-active={filter === chip.id}
              onClick={() => setFilter(chip.id)}
              data-od-id={`timeline-filter-${chip.id}`}
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>

      {shown.length === 0 ? (
        <p className="timeline-empty">No history matches this filter.</p>
      ) : (
        <div className="timeline">
          {shown.map((item) => (
            <div className="t-item" key={item.id}>
              <span className={`t-dot t-dot-${item.tier}`}>
                <TierIcon tier={item.tier} width="9" height="9" />
              </span>
              <div className="t-row">
                <span className="t-title">
                  <span className={`t-tag t-tag-${item.tier}`}>{item.tag}</span>
                  {item.title}
                </span>
                <span className="t-time tabular">{item.date ?? "—"}</span>
              </div>
              {item.assignedTechnician ? (
                <div className="t-desc">Assigned: {item.assignedTechnician}</div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
