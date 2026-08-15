/**
 * MWO-LTSA-050B -- LTSA Open Design Kit, Priority 1 extraction.
 *
 * Evidence: the highest-volume repeated pattern in the archaeology report
 * -- 40+ combined occurrences across SealOpenDesignView.jsx and
 * PumpOpenDesignView.jsx of the exact same 3-node shape:
 * `<div className="info-row"><span className="k">{label}</span>
 * <span className="v">{value}</span></div>`. Two call sites add an extra
 * class to the value span (Hero's Code row: "mono"; every RefGroup-style
 * empty row: "ref-group-empty") -- the only real variation found, hence
 * the single optional `valueClassName` prop.
 *
 * No behavior, no new CSS: `.info-row`/`.k`/`.v` are the exact classes
 * LTSAOpenDesign.css already defines.
 */
export default function InfoRow({ label, value, valueClassName }) {
  return (
    <div className="info-row">
      <span className="k">{label}</span>
      <span className={valueClassName ? `v ${valueClassName}` : "v"}>{value}</span>
    </div>
  );
}
