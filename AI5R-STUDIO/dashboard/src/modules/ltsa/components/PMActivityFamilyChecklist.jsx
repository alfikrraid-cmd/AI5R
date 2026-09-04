import { PM_ACTIVITY_FAMILIES } from "../utils/pmActivityCatalog";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

// MWO-LTSA-PM-ACTIVITY-TAXONOMY-001 -- shared grouped-family activity
// checklist for MANUAL/live PM (create and edit). Replaces the old flat
// 7-checkbox list in both CreatePMOccurrenceModal.jsx and
// PMOccurrenceDetailPanel.jsx's MANUAL branch with one family heading
// per activity type and independent General/DE/NDE toggles beneath it
// (only the variants a family actually has -- Reservoir shows General
// only). General/DE/NDE are three independent checkboxes, never radio
// buttons: DE and NDE may both be checked at once, and checking one
// never affects another.
//
// Visible text next to each checkbox is the short "General"/"DE"/"NDE"
// tag for fast technician entry; the checkbox's own accessible name
// (aria-label) is always the FULL canonical description ("Flushing
// Line", "Flushing Line DE Side", ...) -- the same string used as
// `description` in the activities payload and in any later read-only
// display, so a screen reader, a test's getByLabelText, and the stored
// data all agree on one identity per variant.
//
// AUTO_CHECK_FROM_HISTORY is forbidden: this component only ever
// reflects `doneMap`, a value the caller controls entirely -- it never
// reads history/ConMon/seal_type/api_plan/report style itself. A new PM
// occurrence's caller is expected to start `doneMap` empty so every
// checkbox renders unchecked until a technician explicitly toggles one.
export default function PMActivityFamilyChecklist({ doneMap, onToggle, disabled = false }) {
  return (
    <>
      {PM_ACTIVITY_FAMILIES.map((fam) => (
        <div key={fam.family} style={{ marginBottom: spacing.sm }} data-testid={`activity-family-${fam.family}`}>
          <div style={{ color: colors.text, fontWeight: 600, marginBottom: spacing.xs }}>{fam.family}</div>
          <div style={{ display: "flex", gap: spacing.md, flexWrap: "wrap" }}>
            {fam.variants.map((variant) => (
              <label
                key={variant.code}
                style={{ display: "flex", alignItems: "center", gap: spacing.xs, color: colors.text }}
              >
                <input
                  type="checkbox"
                  aria-label={variant.label}
                  checked={Boolean(doneMap[variant.code])}
                  disabled={disabled}
                  onChange={() => onToggle(variant.code)}
                />
                {variant.side ?? "General"}
              </label>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}
