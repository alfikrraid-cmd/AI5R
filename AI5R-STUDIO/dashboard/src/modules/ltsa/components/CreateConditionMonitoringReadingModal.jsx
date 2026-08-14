import { useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const OPERATING_STATE_OPTIONS = ["Running", "Standby", "Repair"];

const EMPTY_FORM = {
  scheduleCode: "",
  readingDate: "",
  mechsealTempDe: "",
  mechsealTempNde: "",
  suctionTemp: "",
  dischargeTemp: "",
  pumpOperatingState: OPERATING_STATE_OPTIONS[0],
  leakDe: false,
  leakNde: false,
};

const fieldStyle = {
  width: "100%",
  background: colors.panel,
  color: colors.text,
  border: `1px solid ${colors.border}`,
  borderRadius: spacing.xs,
  padding: `${spacing.xs}px ${spacing.sm}px`,
  boxSizing: "border-box",
};

const labelStyle = { display: "block", color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs };
const checkboxLabelStyle = { display: "flex", alignItems: "center", gap: spacing.xs, color: colors.text };

function Field({ id, label, children }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <label htmlFor={id} style={labelStyle}>
        {label}
      </label>
      {children}
    </div>
  );
}

/**
 * Client-state-only, the same disclosed limitation as
 * CreatePMScheduleModal.jsx/CreateCMReportModal.jsx: no backend create
 * route exists for condition_monitoring_reading (WO-CMON-002 exposed
 * list/detail only; the Reading gateway itself has no update/delete
 * either, per WO-CMON-001's disclosed append-only judgment call). This
 * form appends to local page state so the workflow is fully navigable in
 * the UI, without inventing a backend call this MWO's "No new backend"
 * constraint forbids.
 */
export default function CreateConditionMonitoringReadingModal({ isOpen, onClose, onCreate, schedules }) {
  const [form, setForm] = useState(EMPTY_FORM);

  function setField(name) {
    return (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  }

  function setCheckbox(name) {
    return (event) => setForm((current) => ({ ...current, [name]: event.target.checked }));
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (!form.scheduleCode) {
      return;
    }

    const schedule = schedules.find((candidate) => candidate.id === form.scheduleCode);

    onCreate({
      scheduleCode: form.scheduleCode,
      equipmentTag: schedule?.equipmentTag ?? null,
      readingDate: form.readingDate,
      mechsealTempDe: form.mechsealTempDe === "" ? null : Number(form.mechsealTempDe),
      mechsealTempNde: form.mechsealTempNde === "" ? null : Number(form.mechsealTempNde),
      suctionTemp: form.suctionTemp === "" ? null : Number(form.suctionTemp),
      dischargeTemp: form.dischargeTemp === "" ? null : Number(form.dischargeTemp),
      pumpOperatingState: form.pumpOperatingState,
      leakDe: form.leakDe,
      leakNde: form.leakNde,
    });
    setForm(EMPTY_FORM);
  }

  function handleClose() {
    setForm(EMPTY_FORM);
    onClose();
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create Condition Monitoring Reading">
      <form onSubmit={handleSubmit}>
        <Field id="cmon-schedule" label="Schedule">
          <select
            id="cmon-schedule"
            style={fieldStyle}
            value={form.scheduleCode}
            onChange={setField("scheduleCode")}
            required
          >
            <option value="">Select a schedule...</option>
            {schedules.map((schedule) => (
              <option key={schedule.id} value={schedule.id}>
                {schedule.id} — {schedule.equipmentTag}
              </option>
            ))}
          </select>
        </Field>

        <Field id="cmon-reading-date" label="Reading Date">
          <input
            id="cmon-reading-date"
            type="date"
            style={fieldStyle}
            value={form.readingDate}
            onChange={setField("readingDate")}
          />
        </Field>

        <Field id="cmon-mechseal-de" label="Mechseal Temp DE (°C)">
          <input
            id="cmon-mechseal-de"
            type="number"
            style={fieldStyle}
            value={form.mechsealTempDe}
            onChange={setField("mechsealTempDe")}
          />
        </Field>

        <Field id="cmon-mechseal-nde" label="Mechseal Temp NDE (°C)">
          <input
            id="cmon-mechseal-nde"
            type="number"
            style={fieldStyle}
            value={form.mechsealTempNde}
            onChange={setField("mechsealTempNde")}
          />
        </Field>

        <Field id="cmon-suction" label="Suction (°C)">
          <input
            id="cmon-suction"
            type="number"
            style={fieldStyle}
            value={form.suctionTemp}
            onChange={setField("suctionTemp")}
          />
        </Field>

        <Field id="cmon-discharge" label="Discharge (°C)">
          <input
            id="cmon-discharge"
            type="number"
            style={fieldStyle}
            value={form.dischargeTemp}
            onChange={setField("dischargeTemp")}
          />
        </Field>

        <Field id="cmon-operating-state" label="Pump Operating State">
          <select
            id="cmon-operating-state"
            style={fieldStyle}
            value={form.pumpOperatingState}
            onChange={setField("pumpOperatingState")}
          >
            {OPERATING_STATE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>

        <div style={{ marginBottom: spacing.sm, display: "flex", gap: spacing.md }}>
          <label style={checkboxLabelStyle} htmlFor="cmon-leak-de">
            <input id="cmon-leak-de" type="checkbox" checked={form.leakDe} onChange={setCheckbox("leakDe")} />
            Leak (DE)
          </label>

          <label style={checkboxLabelStyle} htmlFor="cmon-leak-nde">
            <input id="cmon-leak-nde" type="checkbox" checked={form.leakNde} onChange={setCheckbox("leakNde")} />
            Leak (NDE)
          </label>
        </div>

        <div style={{ display: "flex", gap: spacing.sm, justifyContent: "flex-end" }}>
          <Button type="button" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit">Create Reading</Button>
        </div>
      </form>
    </Modal>
  );
}
