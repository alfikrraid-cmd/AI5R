/**
 * MWO-LTSA-050B -- LTSA Open Design Kit.
 *
 * Priority 1 extractions only, per the archaeology report: patterns
 * already proven identical (byte-for-byte, or differing only by a single
 * label/value/boolean) across both existing consumers
 * (SealOpenDesignView.jsx, PumpOpenDesignView.jsx). Priority 2/3
 * candidates (ChromeBar, Info Panel, the outer Inspector Rail wrapper,
 * Hero as a whole) are deliberately NOT here -- see the report for why.
 *
 * Folder-of-small-components + index re-export mirrors this codebase's
 * own existing convention (components/engineering-ai/), reused rather
 * than inventing a new organizing pattern.
 */
export { default as Section } from "./Section";
export { default as InfoRow } from "./InfoRow";
export { default as StatusSignal } from "./StatusSignal";
export { default as RailSection } from "./RailSection";
export { default as ActionBar } from "./ActionBar";
export { default as RefGroup } from "./RefGroup";
