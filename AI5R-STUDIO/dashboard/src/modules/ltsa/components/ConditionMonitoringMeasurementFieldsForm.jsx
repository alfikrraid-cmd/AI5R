import { useState } from "react";
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
//
// AI5R-CMON-UX-001 -- the ~38 fields this form renders (15 DE/NDE pairs,
// 5 single fields, operating state, leak DE/NDE) previously appeared as
// one long undifferentiated list -- the confirmed root cause of the
// owner's "visually confusing" complaint. Grouped into named sections
// below, PRESENTATION ONLY: no field is renamed, removed, or invented,
// payload keys/units are exactly as `conditionMonitoringMeasurementFields.js`
// already defines them, and every section is independently collapsible
// -- collapsing a section never clears its values (they live in the
// parent's `measurements` state, entirely untouched by this component's
// own expand/collapse UI state).

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

// Grouping metadata only -- references MEASUREMENT_PAIR_FIELDS entries by
// their existing `group` label, invents nothing. Every pair field is
// assigned to exactly one section; this array is verified 1:1 against
// the canonical list by a dedicated test (no field silently dropped).
const PAIR_SECTIONS = [
  { title: "Vibration", groups: ["Vertical Vibration", "Horizontal Vibration", "Axial Vibration"] },
  { title: "Bearing Temperature", groups: ["Bearing Temp"] },
  { title: "Mechanical Seal / Gland", groups: ["Mechanical Seal Temp", "Stuffing Box Temp", "Seal Gland Temp"], includeLeak: true },
  {
    title: "Flushing / Quench",
    groups: ["Flushing Temp", "Quench Temp", "Flushing In Temp (LBI)", "Flushing Out Temp (LBO)", "Quench Pressure"],
  },
  { title: "Cooling", groups: ["Cooling Water In Temp", "Cooling Water Out Temp", "Water Jacket Temp"] },
];
const PROCESS_CONDITIONS_TITLE = "Process Conditions";

function countRecorded(values) {
  return values.filter((value) => value !== "" && value !== null && value !== undefined).length;
}

function CollapsibleSection({ title, count, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  const bodyId = `cmon-section-${title.replace(/[^a-zA-Z0-9]+/g, "-").toLowerCase()}`;
  return (
    <div style={{ marginBottom: spacing.sm, border: `1px solid ${colors.border}`, borderRadius: spacing.xs }}>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls={bodyId}
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "transparent",
          color: colors.text,
          border: "none",
          padding: `${spacing.sm}px ${spacing.sm}px`,
          cursor: "pointer",
          fontSize: 13,
          fontWeight: 600,
          textAlign: "left",
        }}
      >
        <span>
          {title}
          {count > 0 ? ` · ${count} reading${count === 1 ? "" : "s"}` : ""}
        </span>
        <span aria-hidden="true">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div id={bodyId} style={{ padding: `0 ${spacing.sm}px ${spacing.sm}px` }}>
          {children}
        </div>
      )}
    </div>
  );
}

function PairFieldRow({ field, measurements, onFieldChange, idPrefix }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={labelStyle}>
        {field.group} ({field.unit})
      </div>
      <div style={{ display: "flex", gap: spacing.sm, flexWrap: "wrap" }}>
        <Field id={`${idPrefix}-${field.deKey}`} label={`${field.group} DE`}>
          <div style={{ display: "flex", alignItems: "center", gap: spacing.xs }}>
            <input
              id={`${idPrefix}-${field.deKey}`}
              type="number"
              step="any"
              style={{ ...fieldStyle, flex: 1, minWidth: 0 }}
              value={measurements[field.deKey]}
              onChange={onFieldChange(field.deKey)}
            />
            <span style={{ color: colors.textMuted, fontSize: 12, whiteSpace: "nowrap" }}>{field.unit}</span>
          </div>
        </Field>
        <Field id={`${idPrefix}-${field.ndeKey}`} label={`${field.group} NDE`}>
          <div style={{ display: "flex", alignItems: "center", gap: spacing.xs }}>
            <input
              id={`${idPrefix}-${field.ndeKey}`}
              type="number"
              step="any"
              style={{ ...fieldStyle, flex: 1, minWidth: 0 }}
              value={measurements[field.ndeKey]}
              onChange={onFieldChange(field.ndeKey)}
            />
            <span style={{ color: colors.textMuted, fontSize: 12, whiteSpace: "nowrap" }}>{field.unit}</span>
          </div>
        </Field>
      </div>
    </div>
  );
}

function SingleFieldRow({ field, measurements, onFieldChange, idPrefix }) {
  return (
    <Field id={`${idPrefix}-${field.key}`} label={`${field.label} (${field.unit})`}>
      <div style={{ display: "flex", alignItems: "center", gap: spacing.xs }}>
        <input
          id={`${idPrefix}-${field.key}`}
          type="number"
          step="any"
          style={{ ...fieldStyle, flex: 1, minWidth: 0 }}
          value={measurements[field.key]}
          onChange={onFieldChange(field.key)}
        />
        <span style={{ color: colors.textMuted, fontSize: 12, whiteSpace: "nowrap" }}>{field.unit}</span>
      </div>
    </Field>
  );
}

function LeakRow({ idPrefix, measurements, onFieldChange }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={labelStyle}>{LEAK_FIELD.group}</div>
      <div style={{ display: "flex", gap: spacing.sm, flexWrap: "wrap" }}>
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
  );
}

// `idPrefix` keeps element ids unique when this form is rendered more
// than once on the same page/test tree.
export default function ConditionMonitoringMeasurementFieldsForm({ measurements, onFieldChange, idPrefix = "cmon" }) {
  const pairFieldsByGroup = new Map(MEASUREMENT_PAIR_FIELDS.map((field) => [field.group, field]));

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

      {PAIR_SECTIONS.map((section) => {
        const fields = section.groups.map((group) => pairFieldsByGroup.get(group)).filter(Boolean);
        const values = fields.flatMap((field) => [measurements[field.deKey], measurements[field.ndeKey]]);
        if (section.includeLeak) {
          values.push(measurements[LEAK_FIELD.deKey], measurements[LEAK_FIELD.ndeKey]);
        }
        return (
          <CollapsibleSection key={section.title} title={section.title} count={countRecorded(values)}>
            {fields.map((field) => (
              <PairFieldRow key={field.group} field={field} measurements={measurements} onFieldChange={onFieldChange} idPrefix={idPrefix} />
            ))}
            {section.includeLeak && <LeakRow idPrefix={idPrefix} measurements={measurements} onFieldChange={onFieldChange} />}
          </CollapsibleSection>
        );
      })}

      <CollapsibleSection
        title={PROCESS_CONDITIONS_TITLE}
        count={countRecorded(MEASUREMENT_SINGLE_FIELDS.map((field) => measurements[field.key]))}
      >
        {MEASUREMENT_SINGLE_FIELDS.map((field) => (
          <SingleFieldRow key={field.key} field={field} measurements={measurements} onFieldChange={onFieldChange} idPrefix={idPrefix} />
        ))}
      </CollapsibleSection>
    </>
  );
}
