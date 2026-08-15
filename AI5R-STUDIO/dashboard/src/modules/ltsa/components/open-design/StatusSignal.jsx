/**
 * MWO-LTSA-050B -- LTSA Open Design Kit, Priority 1 extraction.
 *
 * Evidence: ~10-12 combined occurrences across both view files of
 * `<span className="status-signal {tier}"><span className="dot-lg" />
 * {label}</span>` (Hero status, LTSA Coverage badge, Recommended
 * Replacement footer, Inspector Rail Health/Criticality) -- one clean
 * binary variation: the Engineering AI unavailable-state badge omits the
 * dot (`<span className="status-signal {variant}">{label}</span>`, no
 * dot-lg child at all). `dot` defaults to true (the majority shape); the
 * Engineering AI call site is the only one that passes `dot={false}`.
 *
 * The conditional preserves the exact original whitespace behavior: with
 * a dot, a literal space separates the dot glyph from the label (JSX's
 * `<span/> {label}` text-node behavior); without a dot, there is no
 * leading space at all.
 *
 * No behavior, no new CSS: `.status-signal`/`.dot-lg` are the exact
 * classes LTSAOpenDesign.css already defines.
 */
export default function StatusSignal({ tier, label, dot = true }) {
  return (
    <span className={`status-signal ${tier}`}>
      {dot ? (<><span className="dot-lg" /> {label}</>) : label}
    </span>
  );
}
