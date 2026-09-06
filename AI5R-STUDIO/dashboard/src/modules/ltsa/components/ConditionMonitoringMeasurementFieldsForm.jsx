import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { MEASUREMENT_PAIR_FIELDS, MEASUREMENT_SINGLE_FIELDS, LEAK_FIELD } from "../utils/conditionMonitoringMeasurementFields";

// MWO-LTSA-CMON-ADHOC-ENTRY-001 -- extracted, unchanged, from
// CreateConditionMonitoringReadingModal.jsx (which now imports this same
// component instead of its own inline copy) so the schedule-based Create
// form and the new ad-hoc Create form render the exact same DE/NDE grid
// and leak tri-state control -- one implementation, never two that could
// drift apart. Every field still comes from the one shared data module
// (conditionMonitoringMeasurementFields.js); this file adds no new field,
// no new catalog, only presentation.

export const OPERATING_STATE_OPTIONS = ["Running", "Standby", "Repair"];

export const fieldStyle = {
  width: "100%",
  background: colors.panel,
  color: colors.text,
  border: `1px solid ${colors.border}`,
  borderRadius: spacing.xs,
  padding: `${spacing.xs}px ${spacing.sm}px`,
  boxSizing: "border-box",
};

export const labelStyle = { display: "block", color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs };

export function Field({ id, label, children }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <label htmlFor={id} style={labelStyle}>
        {label}
      </label>
      {children}
    </div>
  );
}

export const LEAK_OPTIONS = [
  { value: "", label: "Not Recorded" },
  { value: "false", label: "No Leak" },
  { value: "true", label: "Leak Detected" },
];

// `idPrefix` keeps element ids unique when this form is rendered more
// than once on the same page/test tree (e.g. the schedule-based and
// ad-hoc Create modals never coexist in the DOM at once today, but two
// independent id prefixes cost nothing and remove that assumption).
export default function ConditionMonitoringMeasurementFieldsForm({ measurements, onFieldChange, idPrefix = "cmon" }) {
  return (
    <>
      <Field id={`${idPrefix}-operating-state`} label="Pump Operating State">
        <select
          id={`${idPrefix}-operating-state`}
          style={fieldStyle}
          value={measurements.pumpOperatingState}
          onChange={onFieldChange("pumpOperatingState")}
        >
          <option value="">Not Recorded</option>
          {OPERATING_STATE_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </Field>

      {/* Every canonical DE/NDE measurement pair (golden-evidence-
          established, migration 014's own header), rendered from the one
          shared field list. DE/NDE are always two separate inputs --
          never collapsed into one, never a General option (the schema
          has none for these fields). */}
      {MEASUREMENT_PAIR_FIELDS.map((field) => (
        <div key={field.group} style={{ marginBottom: spacing.sm }}>
          <div style={labelStyle}>
            {field.group} ({field.unit})
          </div>
          <div style={{ display: "flex", gap: spacing.sm }}>
            <Field id={`${idPrefix}-${field.deKey}`} label={`${field.group} DE`}>
              <input
                id={`${idPrefix}-${field.deKey}`}
                type="number"
                step="any"
                style={fieldStyle}
                value={measurements[field.deKey]}
                onChange={onFieldChange(field.deKey)}
              />
            </Field>
            <Field id={`${idPrefix}-${field.ndeKey}`} label={`${field.group} NDE`}>
              <input
                id={`${idPrefix}-${field.ndeKey}`}
                type="number"
                step="any"
                style={fieldStyle}
                value={measurements[field.ndeKey]}
                onChange={onFieldChange(field.ndeKey)}
              />
            </Field>
          </div>
        </div>
      ))}

      {MEASUREMENT_SINGLE_FIELDS.map((field) => (
        <Field key={field.key} id={`${idPrefix}-${field.key}`} label={`${field.label} (${field.unit})`}>
          <input
            id={`${idPrefix}-${field.key}`}
            type="number"
            step="any"
            style={fieldStyle}
            value={measurements[field.key]}
            onChange={onFieldChange(field.key)}
          />
        </Field>
      ))}

      {/* Leakage: tri-state, never inferred. A blank selection persists
          as NULL (not recorded), never as "no leak". */}
      <div style={{ marginBottom: spacing.sm }}>
        <div style={labelStyle}>{LEAK_FIELD.group}</div>
        <div style={{ display: "flex", gap: spacing.sm }}>
          <Field id={`${idPrefix}-${LEAK_FIELD.deKey}`} label={`${LEAK_FIELD.group} DE`}>
            <select
              id={`${idPrefix}-${LEAK_FIELD.deKey}`}
              style={fieldStyle}
              value={measurements[LEAK_FIELD.deKey]}
              onChange={onFieldChange(LEAK_FIELD.deKey)}
            >
              {LEAK_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
          <Field id={`${idPrefix}-${LEAK_FIELD.ndeKey}`} label={`${LEAK_FIELD.group} NDE`}>
            <select
              id={`${idPrefix}-${LEAK_FIELD.ndeKey}`}
              style={fieldStyle}
              value={measurements[LEAK_FIELD.ndeKey]}
              onChange={onFieldChange(LEAK_FIELD.ndeKey)}
            >
              {LEAK_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </div>
    </>
  );
}
