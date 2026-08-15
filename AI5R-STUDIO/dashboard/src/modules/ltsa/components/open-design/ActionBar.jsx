/**
 * MWO-LTSA-050B -- LTSA Open Design Kit, Priority 1 extraction.
 *
 * Evidence: both view files' sticky Action Bar share an identical
 * 4-level wrapper (.action-bar > .action-bar-inner >
 * .action-bar-status[.label + .meta] + .action-bar-actions) AND an
 * identical two-line status composition -- line 1 is always
 * "{primary identity} · {status label}" (built by the caller and passed
 * as `label`, since the exact join differs only by which two facts are
 * joined, not by structure), line 2 is always
 * "{coverage/primary meta} · {a domain metric label} {that metric's
 * value}" (Seal: "LTSA Covered · Stock 12"; Pump: "LTSA Covered ·
 * Criticality High") -- decomposed here as `metaPrimary`/`metaLabel`/
 * `metaValue` since only the label word and the value differ, not the
 * join pattern itself. Action buttons vary in number and content between
 * the two workspaces (Seal: 1-2 buttons; Pump: 3), so they are passed as
 * `children` into the already-identical `.action-bar-actions` container
 * rather than templated.
 *
 * No behavior, no new CSS: every class here is one LTSAOpenDesign.css
 * already defines.
 */
export default function ActionBar({ label, metaPrimary, metaLabel, metaValue, children }) {
  return (
    <div className="action-bar" data-od-id="action-bar">
      <div className="action-bar-inner">
        <div className="action-bar-status">
          <span className="label">{label}</span>
          <span className="meta">{metaPrimary} · {metaLabel} {metaValue}</span>
        </div>
        <div className="action-bar-actions">
          {children}
        </div>
      </div>
    </div>
  );
}
