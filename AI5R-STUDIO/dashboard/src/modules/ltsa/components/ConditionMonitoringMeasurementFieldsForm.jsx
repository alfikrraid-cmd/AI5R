import { useState } from "react";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { MEASUREMENT_PAIR_FIELDS, MEASUREMENT_SINGLE_FIELDS, LEAK_FIELD } from "../utils/conditionMonitoringMeasurementFields";

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

export const srOnlyStyle = {
  position: "absolute",
  width: "1px",
  height: "1px",
  padding: "0",
  margin: "-1px",
  overflow: "hidden",
  clip: "rect(0, 0, 0, 0)",
  whiteSpace: "nowrap",
  border: "0",
};

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

function CollapsibleSection({ title, count, isOpen, onToggle, defaultOpen = false, children }) {
  const [localOpen, setLocalOpen] = useState(defaultOpen);
  const open = isOpen !== undefined ? isOpen : localOpen;
  const toggle = onToggle ? onToggle : () => setLocalOpen((current) => !current);
  const bodyId = `cmon-section-${title.replace(/[^a-zA-Z0-9]+/g, "-").toLowerCase()}`;

  return (
    <div style={{ marginBottom: spacing.sm, border: `1px solid ${colors.border}`, borderRadius: spacing.xs, background: colors.panel }}>
      <button
        type="button"
        onClick={toggle}
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

function PairFieldTableRow({ field, measurements, onFieldChange, idPrefix }) {
  return (
    <tr style={{ borderBottom: `1px solid ${colors.border}44` }}>
      <td style={{ padding: "6px 8px", color: colors.text, verticalAlign: "middle" }}>
        <span style={{ fontWeight: 500 }}>{field.group} ({field.unit})</span>
      </td>
      <td style={{ padding: "6px 8px", verticalAlign: "middle" }}>
        <div>
          <label htmlFor={`${idPrefix}-${field.deKey}`} style={srOnlyStyle}>
            {field.group} DE
          </label>
          <input
            id={`${idPrefix}-${field.deKey}`}
            aria-label={`${field.group} DE`}
            type="number"
            step="any"
            placeholder="—"
            style={{ ...fieldStyle, padding: "4px 8px", fontSize: 12 }}
            value={measurements[field.deKey]}
            onChange={onFieldChange(field.deKey)}
          />
        </div>
      </td>
      <td style={{ padding: "6px 8px", verticalAlign: "middle" }}>
        <div>
          <label htmlFor={`${idPrefix}-${field.ndeKey}`} style={srOnlyStyle}>
            {field.group} NDE
          </label>
          <input
            id={`${idPrefix}-${field.ndeKey}`}
            aria-label={`${field.group} NDE`}
            type="number"
            step="any"
            placeholder="—"
            style={{ ...fieldStyle, padding: "4px 8px", fontSize: 12 }}
            value={measurements[field.ndeKey]}
            onChange={onFieldChange(field.ndeKey)}
          />
        </div>
      </td>
      <td style={{ padding: "6px 8px", color: colors.textMuted, fontSize: 12, verticalAlign: "middle" }}>
        {field.unit}
      </td>
    </tr>
  );
}

function LeakTableRow({ idPrefix, measurements, onFieldChange }) {
  return (
    <tr style={{ borderBottom: `1px solid ${colors.border}44` }}>
      <td style={{ padding: "6px 8px", color: colors.text, verticalAlign: "middle" }}>
        <span style={{ fontWeight: 500 }}>{LEAK_FIELD.group}</span>
      </td>
      <td style={{ padding: "6px 8px", verticalAlign: "middle" }}>
        <div>
          <label htmlFor={`${idPrefix}-${LEAK_FIELD.deKey}`} style={srOnlyStyle}>
            {LEAK_FIELD.group} DE
          </label>
          <select
            id={`${idPrefix}-${LEAK_FIELD.deKey}`}
            aria-label={`${LEAK_FIELD.group} DE`}
            style={{ ...fieldStyle, padding: "4px 8px", fontSize: 12 }}
            value={measurements[LEAK_FIELD.deKey]}
            onChange={onFieldChange(LEAK_FIELD.deKey)}
          >
            {LEAK_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </td>
      <td style={{ padding: "6px 8px", verticalAlign: "middle" }}>
        <div>
          <label htmlFor={`${idPrefix}-${LEAK_FIELD.ndeKey}`} style={srOnlyStyle}>
            {LEAK_FIELD.group} NDE
          </label>
          <select
            id={`${idPrefix}-${LEAK_FIELD.ndeKey}`}
            aria-label={`${LEAK_FIELD.group} NDE`}
            style={{ ...fieldStyle, padding: "4px 8px", fontSize: 12 }}
            value={measurements[LEAK_FIELD.ndeKey]}
            onChange={onFieldChange(LEAK_FIELD.ndeKey)}
          >
            {LEAK_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </td>
      <td style={{ padding: "6px 8px", color: colors.textMuted, fontSize: 12, verticalAlign: "middle" }}>
        Status
      </td>
    </tr>
  );
}

function PairSectionTable({ fields, includeLeak, measurements, onFieldChange, idPrefix }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${colors.border}`, color: colors.textMuted }}>
            <th style={{ padding: "6px 8px", textAlign: "left", fontWeight: 600 }}>Parameter</th>
            <th style={{ padding: "6px 8px", textAlign: "left", width: "30%", fontWeight: 600 }}>Drive End (DE)</th>
            <th style={{ padding: "6px 8px", textAlign: "left", width: "30%", fontWeight: 600 }}>Non-Drive End (NDE)</th>
            <th style={{ padding: "6px 8px", textAlign: "left", width: "12%", fontWeight: 600 }}>Unit</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((field) => (
            <PairFieldTableRow
              key={field.group}
              field={field}
              measurements={measurements}
              onFieldChange={onFieldChange}
              idPrefix={idPrefix}
            />
          ))}
          {includeLeak && (
            <LeakTableRow
              idPrefix={idPrefix}
              measurements={measurements}
              onFieldChange={onFieldChange}
            />
          )}
        </tbody>
      </table>
    </div>
  );
}

function SingleFieldRow({ field, measurements, onFieldChange, idPrefix }) {
  return (
    <Field id={`${idPrefix}-${field.key}`} label={`${field.label} (${field.unit})`}>
      <div style={{ display: "flex", alignItems: "center", gap: spacing.xs }}>
        <input
          id={`${idPrefix}-${field.key}`}
          aria-label={`${field.label} (${field.unit})`}
          type="number"
          step="any"
          placeholder="—"
          style={{ ...fieldStyle, flex: 1, minWidth: 0, padding: "4px 8px", fontSize: 12 }}
          value={measurements[field.key]}
          onChange={onFieldChange(field.key)}
        />
        <span style={{ color: colors.textMuted, fontSize: 12, whiteSpace: "nowrap" }}>{field.unit}</span>
      </div>
    </Field>
  );
}

export default function ConditionMonitoringMeasurementFieldsForm({ measurements, onFieldChange, idPrefix = "cmon" }) {
  const pairFieldsByGroup = new Map(MEASUREMENT_PAIR_FIELDS.map((field) => [field.group, field]));

  const [sectionOpenStates, setSectionOpenStates] = useState({
    Vibration: false,
    "Bearing Temperature": false,
    "Mechanical Seal / Gland": false,
    "Flushing / Quench": false,
    Cooling: false,
    "Process Conditions": false,
  });

  const allOpen = Object.values(sectionOpenStates).every(Boolean);

  function toggleAll() {
    const nextState = !allOpen;
    setSectionOpenStates({
      Vibration: nextState,
      "Bearing Temperature": nextState,
      "Mechanical Seal / Gland": nextState,
      "Flushing / Quench": nextState,
      Cooling: nextState,
      "Process Conditions": nextState,
    });
  }

  function toggleSection(title) {
    setSectionOpenStates((prev) => ({ ...prev, [title]: !prev[title] }));
  }

  return (
    <>
      <div
        style={{
          marginBottom: spacing.md,
          padding: spacing.sm,
          border: `1px solid ${colors.border}`,
          borderRadius: spacing.xs,
          background: colors.panel,
        }}
      >
        <Field id={`${idPrefix}-operating-state`} label="Pump Operating State">
          <select
            id={`${idPrefix}-operating-state`}
            aria-label="Pump Operating State"
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
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: spacing.xs,
          padding: `0 ${spacing.xs}px`,
        }}
      >
        <span style={{ fontSize: 11, color: colors.textMuted, fontWeight: 600, letterSpacing: 0.5 }}>
          MEASUREMENT GROUPS (DE / NDE)
        </span>
        <button
          type="button"
          onClick={toggleAll}
          style={{
            background: "transparent",
            border: "none",
            color: colors.info,
            fontSize: 12,
            fontWeight: 600,
            cursor: "pointer",
            padding: "2px 6px",
          }}
        >
          {allOpen ? "Collapse All ▴" : "Expand All ▾"}
        </button>
      </div>

      {PAIR_SECTIONS.map((section) => {
        const fields = section.groups.map((group) => pairFieldsByGroup.get(group)).filter(Boolean);
        const values = fields.flatMap((field) => [measurements[field.deKey], measurements[field.ndeKey]]);
        if (section.includeLeak) {
          values.push(measurements[LEAK_FIELD.deKey], measurements[LEAK_FIELD.ndeKey]);
        }
        return (
          <CollapsibleSection
            key={section.title}
            title={section.title}
            count={countRecorded(values)}
            isOpen={sectionOpenStates[section.title]}
            onToggle={() => toggleSection(section.title)}
          >
            <PairSectionTable
              fields={fields}
              includeLeak={section.includeLeak}
              measurements={measurements}
              onFieldChange={onFieldChange}
              idPrefix={idPrefix}
            />
          </CollapsibleSection>
        );
      })}

      <CollapsibleSection
        title={PROCESS_CONDITIONS_TITLE}
        count={countRecorded(MEASUREMENT_SINGLE_FIELDS.map((field) => measurements[field.key]))}
        isOpen={sectionOpenStates[PROCESS_CONDITIONS_TITLE]}
        onToggle={() => toggleSection(PROCESS_CONDITIONS_TITLE)}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: spacing.sm,
            paddingTop: spacing.xs,
          }}
        >
          {MEASUREMENT_SINGLE_FIELDS.map((field) => (
            <SingleFieldRow key={field.key} field={field} measurements={measurements} onFieldChange={onFieldChange} idPrefix={idPrefix} />
          ))}
        </div>
      </CollapsibleSection>
    </>
  );
}
