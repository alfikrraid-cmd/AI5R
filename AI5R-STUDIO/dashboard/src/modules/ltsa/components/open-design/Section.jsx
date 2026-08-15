/**
 * MWO-LTSA-050B -- LTSA Open Design Kit, Priority 1 extraction.
 *
 * Evidence (see the MWO-LTSA-050B archaeology report): 16 of the 18
 * `.assessment-section` blocks across SealOpenDesignView.jsx and
 * PumpOpenDesignView.jsx followed this exact shape byte-for-byte --
 * `<section className="assessment-section" data-od-id="X"><span
 * className="eyebrow">Y</span>{content}</section>` -- before this
 * extraction. The two that don't (both files' Documents section, which
 * pairs its eyebrow with a button inside `.section-head`) keep using raw
 * markup rather than being forced through this component -- see the
 * report for why bending Section to fit them would be the "abstraction
 * for the sake of abstraction" this MWO explicitly forbids.
 *
 * No behavior, no new CSS: `.assessment-section`/`.eyebrow` are the exact
 * classes LTSAOpenDesign.css already defines.
 */
export default function Section({ id, title, children }) {
  return (
    <section className="assessment-section" data-od-id={id}>
      {title && <span className="eyebrow">{title}</span>}
      {children}
    </section>
  );
}
