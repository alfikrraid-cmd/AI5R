// MWO-LTSA-PM-ACTIVITY-TAXONOMY-001 -- the smallest catalog supported by
// verified Phase 4C source evidence (19 distinct activity labels observed
// across the 540 V2-recovered historical PM occurrences), replacing the
// old flat 7-item ACTIVITY_OPTIONS (CreatePMOccurrenceModal.jsx/
// PMOccurrenceDetailPanel.jsx, now both migrated to this shared module).
//
// Every family/variant below is directly evidenced -- none invented:
//   Flushing Line / DE / NDE Side   -- General 199, DE 86, NDE 86
//   Quench Line / DE / NDE Side     -- General 163, DE 29, NDE 29
//   Strainer / DE / NDE Side        -- General 81, DE 16, NDE 16
//   Check Valve / DE / NDE Side     -- General 19, DE 13, NDE 8
//   Reservoir (no DE/NDE evidenced) -- General only, 0 sided occurrences
//   Cooler / DE / NDE Side          -- General 53, DE 18, NDE 18
//   Cooling Water Cooler / DE / NDE -- General 121, DE 18, NDE 18
//
// "Cooler" and "Cooling Water Cooler" are DISTINCT families -- migration
// 014's own header (read directly from the December 2022 golden report,
// page 34/35) lists them as two separate named checklist items
// ("Cooler/DE/NDE" and "Cooling Water Cooler Line/DE/NDE"), never merged
// here. "Cooler" carries an internal-only semantic (Water-Cooled Heat
// Exchanger) that is NEVER surfaced in any display label -- the family
// name and every variant description below say "Cooler", nothing else.
//
// legacyCode preserves the 7 pre-existing numeric identifiers (still
// readable/backward-compatible) so an OLD manual PM record's activities
// array (which only ever carried these numbers) keeps matching correctly
// after this catalog expansion. NEW selections always emit the new
// stable string `code`, never a legacy number -- this is a deliberate,
// disclosed payload-contract evolution (Phase 4D), not a compatibility
// break: the backend's `activities` JSONB/PMActivityEntry model already
// accepts any code string unconstrained (Phase 4C's own CODE_TRACER
// finding), so old and new codes coexist with zero backend change.
//
// Canonical future spelling is "Reservoir" (matches the golden report's
// own spelling, per migration 014, and the pre-existing ACTIVITY_OPTIONS
// entry) -- the historical "Resevoir" typo some already-promoted records
// carry is NEVER touched by this catalog; historical rendering stays on
// its own separate Phase 4B code path (HistoricalActivitiesPerformed in
// PMOccurrenceDetailPanel.jsx), which reads stored description text
// verbatim and never consults this catalog at all.
export const PM_ACTIVITY_FAMILIES = [
  {
    family: "Flushing Line",
    variants: [
      { code: "FLUSHING_LINE", legacyCode: "1", side: null, label: "Flushing Line" },
      { code: "FLUSHING_LINE_DE", legacyCode: null, side: "DE", label: "Flushing Line DE Side" },
      { code: "FLUSHING_LINE_NDE", legacyCode: null, side: "NDE", label: "Flushing Line NDE Side" },
    ],
  },
  {
    family: "Quench Line",
    variants: [
      { code: "QUENCH_LINE", legacyCode: "4", side: null, label: "Quench Line" },
      { code: "QUENCH_LINE_DE", legacyCode: null, side: "DE", label: "Quench Line DE Side" },
      { code: "QUENCH_LINE_NDE", legacyCode: null, side: "NDE", label: "Quench Line NDE Side" },
    ],
  },
  {
    family: "Strainer",
    variants: [
      { code: "STRAINER", legacyCode: "19", side: null, label: "Strainer" },
      { code: "STRAINER_DE", legacyCode: null, side: "DE", label: "Strainer DE Side" },
      { code: "STRAINER_NDE", legacyCode: null, side: "NDE", label: "Strainer NDE Side" },
    ],
  },
  {
    family: "Check Valve",
    variants: [
      { code: "CHECK_VALVE", legacyCode: null, side: null, label: "Check Valve" },
      { code: "CHECK_VALVE_DE", legacyCode: "17", side: "DE", label: "Check Valve DE Side" },
      { code: "CHECK_VALVE_NDE", legacyCode: "18", side: "NDE", label: "Check Valve NDE Side" },
    ],
  },
  {
    // No DE/NDE evidenced anywhere in the 540 -- General only, never
    // given sided variants that no source row ever supports.
    family: "Reservoir",
    variants: [{ code: "RESERVOIR", legacyCode: "6", side: null, label: "Reservoir" }],
  },
  {
    // WCH (Water-Cooled Heat Exchanger) is the internal-only semantic
    // for this family -- never displayed. Distinct from Cooling Water
    // Cooler below; never merged.
    family: "Cooler",
    variants: [
      { code: "COOLER", legacyCode: null, side: null, label: "Cooler" },
      { code: "COOLER_DE", legacyCode: null, side: "DE", label: "Cooler DE Side" },
      { code: "COOLER_NDE", legacyCode: null, side: "NDE", label: "Cooler NDE Side" },
    ],
  },
  {
    family: "Cooling Water Cooler",
    variants: [
      { code: "COOLING_WATER_COOLER", legacyCode: "8", side: null, label: "Cooling Water Cooler" },
      { code: "COOLING_WATER_COOLER_DE", legacyCode: null, side: "DE", label: "Cooling Water Cooler DE Side" },
      { code: "COOLING_WATER_COOLER_NDE", legacyCode: null, side: "NDE", label: "Cooling Water Cooler NDE Side" },
    ],
  },
];

// Flattened, in catalog order -- convenient for payload-building and
// lookup without re-walking the family/variant nesting at every call
// site.
export const PM_ACTIVITY_VARIANTS = PM_ACTIVITY_FAMILIES.flatMap((f) => f.variants);

// MWO-LTSA-PM-ACTIVITY-TAXONOMY-001 -- reads a stored pm_occurrence.
// activities array (any shape: new string codes, legacy numeric codes,
// or a mix) and returns { [variant.code]: boolean } for every catalog
// variant. Matches an entry by its NEW code first, falling back to the
// variant's legacyCode -- so an old manual record (which only ever
// carried "1".."19") keeps rendering correctly against the expanded
// catalog with zero migration. Never matches by description text alone
// (that would risk silently reinterpreting a historical import's own
// wording); this function is for MANUAL-provenance records only --
// historical rendering never calls it (see HistoricalActivitiesPerformed,
// PMOccurrenceDetailPanel.jsx, Phase 4B, untouched by this module).
export function buildDoneMapFromActivities(activities) {
  const doneMap = {};
  const entries = Array.isArray(activities) ? activities : [];
  for (const variant of PM_ACTIVITY_VARIANTS) {
    const match = entries.find(
      (entry) => entry?.code === variant.code || (variant.legacyCode !== null && entry?.code === variant.legacyCode)
    );
    doneMap[variant.code] = Boolean(match?.done);
  }
  return doneMap;
}

// Builds the full activities payload for create/save, preserving the
// existing contract established by the old ACTIVITY_OPTIONS.map(...)
// call sites: every catalog variant is included (not just checked
// ones), each carrying its own stable NEW code, full description, side,
// and a done flag reflecting the current selection. AUTO_CHECK_FROM_
// HISTORY is forbidden by design here: `doneMap` only ever reflects
// explicit technician toggles (never pre-populated from history/ConMon/
// seal_type/api_plan/report style by any caller of this function).
export function buildActivitiesPayload(doneMap) {
  return PM_ACTIVITY_VARIANTS.map((variant) => ({
    code: variant.code,
    description: variant.label,
    side: variant.side,
    done: Boolean(doneMap[variant.code]),
  }));
}
