/**
 * MWO-LTSA-050B -- LTSA Open Design Kit, Priority 1 extraction.
 *
 * Evidence: all 9 combined Inspector Rail entries across both view files
 * (5 in Seal: Health/Lifecycle/Criticality/Recommendation/Recent
 * Activities; 4 in Pump: Health/Criticality/Recommendation/Recent
 * Activities) follow this exact shape with zero deviation --
 * `<div className="rail-section" data-od-id="X"><h3 className="rail-title">
 * {title}</h3>{content}</div>`. The strongest-evidenced candidate in the
 * report alongside RefGroup and InfoRow.
 *
 * The outer `<aside className="inspector-rail">` wrapper is NOT extracted
 * here -- it appears only once per file (not a repeated pattern within
 * either file), so wrapping it would be exactly the "abstraction for the
 * sake of abstraction" this MWO forbids; see the archaeology report.
 *
 * No behavior, no new CSS: `.rail-section`/`.rail-title` are the exact
 * classes LTSAOpenDesign.css already defines.
 */
export default function RailSection({ id, title, children }) {
  return (
    <div className="rail-section" data-od-id={id}>
      <h3 className="rail-title">{title}</h3>
      {children}
    </div>
  );
}
