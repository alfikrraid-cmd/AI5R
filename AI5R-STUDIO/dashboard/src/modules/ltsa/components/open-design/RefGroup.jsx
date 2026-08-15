/**
 * MWO-LTSA-050B -- LTSA Open Design Kit, Priority 1 extraction.
 *
 * Evidence: this function was defined twice, byte-for-byte identical, in
 * SealOpenDesignView.jsx (since MWO-LTSA-042A, refined through
 * MWO-LTSA-047/048) and PumpOpenDesignView.jsx (MWO-LTSA-050, which
 * explicitly copied it verbatim and documented the duplication in its own
 * header comment as deferred, not accidental, pending this exact
 * extraction). The strongest-evidenced candidate in the archaeology
 * report -- zero divergence, not even a comment differs.
 *
 * Behavior unchanged: empty groups render a compact "0 · <reason>" row
 * (an empty group's item count is a real, known fact -- zero -- not
 * "unknown", per MWO-LTSA-047/048); populated groups render full
 * `.part-item` rows with their own flag/meta. `emptyReason` stays
 * optional -- callers that don't distinguish "no LTSA association" from
 * "no engineering data" simply omit it, exactly as before.
 *
 * No new CSS: every class here is one LTSAOpenDesign.css already defines.
 *
 * MWO-LTSA-070 -- optional per-item `onClick`, additive and backward
 * compatible: every existing caller that never sets `item.onClick`
 * renders the exact same static `<span>` as before, byte-for-byte. When
 * `onClick` is present, the item name renders as a `<button>` instead, so
 * the row becomes keyboard- and screen-reader-operable, not just
 * mouse-clickable. No new CSS class: `.part-name`'s existing font-size/
 * font-weight rule (LTSAOpenDesign.css) still applies to the button via
 * the same class name -- only the browser's default button chrome
 * (background/border/padding/alignment) is reset inline, the same
 * "small one-off style override" convention already used throughout
 * these Open Design views (e.g. PumpOpenDesignView.jsx's own
 * `style={{ marginTop: ... }}` usages).
 */
export default function RefGroup({ title, items, emptyReason }) {
  if (items.length === 0) {
    return (
      <div className="info-row">
        <span className="k">{title}</span>
        <span className="v ref-group-empty">0{emptyReason ? ` · ${emptyReason}` : ""}</span>
      </div>
    );
  }
  return (
    <div style={{ marginBottom: "var(--space-5)" }}>
      <span className="eyebrow" style={{ display: "block", marginBottom: "var(--space-2)" }}>{title}</span>
      {items.map((item, i) => (
        <div className="part-item" key={item.key ?? i}>
          <div className="part-row">
            {item.onClick ? (
              <button
                type="button"
                className="part-name"
                style={{ background: "none", border: "none", padding: 0, color: "inherit", cursor: "pointer", textAlign: "left" }}
                onClick={item.onClick}
                data-od-id={item.dataOdId}
              >
                {item.name}
              </button>
            ) : (
              <span className="part-name">{item.name}</span>
            )}
            {item.flagLabel && <span className={`stock-flag ${item.flag || "ok"}`}>{item.flagLabel}</span>}
          </div>
          {item.meta && <div className="part-meta">{item.meta}</div>}
        </div>
      ))}
    </div>
  );
}
