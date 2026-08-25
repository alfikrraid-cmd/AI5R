import { useState } from "react";

// MWO-LTSA-032A -- KnowledgeSection: Header + Badge + Collapse + Body +
// Footer, per the approved Open Design spec §4b. Every one of the 11
// sections uses this same structure -- no per-section variant. Collapse
// mechanism (native <button aria-expanded aria-controls>, chevron rotate)
// mirrors the base design's own copy of Explorer's collapse toggle
// (Repository Archaeology found no real ExplorerGroup component to import
// -- see the deliverable report's Reuse Analysis).
export default function KnowledgeSection({ id, title, badge, defaultOpen = true, footer, children }) {
  const [open, setOpen] = useState(defaultOpen);
  const bodyId = `kn-section-body-${id}`;

  return (
    <section className="rail-section" id={`kn-section-${id}`} data-testid={`knowledge-section-${id}`}>
      <button
        type="button"
        className="kn-section-head"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen((current) => !current)}
      >
        <span className="kn-section-head-left">
          <h3 className="rail-title">{title}</h3>
        </span>
        <span className="kn-section-head-left">
          {badge != null ? <span className="kn-badge">{badge}</span> : null}
          <ChevronIcon className="chev" />
        </span>
      </button>
      <div id={bodyId} className="kn-section-body" data-open={open} aria-live="polite">
        {children}
        <div className="kn-section-footer">{footer ?? null}</div>
      </div>
    </section>
  );
}

function ChevronIcon({ className }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
