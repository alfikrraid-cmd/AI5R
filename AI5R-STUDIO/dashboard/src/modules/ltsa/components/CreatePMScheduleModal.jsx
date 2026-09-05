import { useEffect, useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { nextMonthFirstDay } from "../utils/pmMapping";
import PMActivityFamilyChecklist from "./PMActivityFamilyChecklist";
import AssetSelector from "./AssetSelector";
import { buildPlannedActivitiesPayload } from "../utils/pmActivityCatalog";
import { getPumps } from "../../../api/ai5rClient";
import { mapPumpRecord } from "../utils/pumpMapping";

const FREQUENCY_OPTIONS = [
  { value: "DAILY", label: "Daily" },
  { value: "WEEKLY", label: "Weekly" },
  { value: "MONTHLY", label: "Monthly" },
  { value: "RUNTIME_BASED", label: "Runtime-based" },
];

// AI5R-PHASE4E2, Section B -- Trigger Type is a required backend/DB field
// (pm_schedule.trigger_type TEXT NOT NULL) with ZERO business-logic
// readers anywhere in the codebase (confirmed by a full-repo grep: every
// non-test reference is either this literal string, a pure display label
// (triggerTypeLabel/InfoRow), or the column definition itself -- no
// recurrence engine or scheduling logic branches on it, because no
// recurrence engine exists in this phase). Every existing record (live
// code paths and sample data alike) already carries a strict 1:1
// correlation with frequency: DAILY/WEEKLY/MONTHLY -> CALENDAR,
// RUNTIME_BASED -> METER, with zero exceptions. Deriving it here is
// therefore safe and changes no recurrence behavior -- it only removes a
// redundant manual choice from the create form (never surfaced to the
// user, per Section B's own preference).
function deriveTriggerType(frequency) {
  return frequency === "RUNTIME_BASED" ? "METER" : "CALENDAR";
}

// AI5R-PHASE4E1 -- OWNER DECISIONS 1-5: Schedule Code is now system-
// generated (never typed by a human, so it has no field here at all) and
// Procedure is no longer a required user-facing field (replaced by an
// optional "Notes" field, mapped onto the same existing `procedure`
// column by PM.jsx's handleCreate -- see that file for the mapping).
//
// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- "Normal operational UI should
// create schedules for NEXT MONTH... Derive next calendar month from
// current operational date." A function, not a static value, so the
// default is computed fresh each time the modal opens (see
// initialFormFor's own useEffect below) rather than frozen at module load.
function emptyForm() {
  return {
    notes: "",
    equipmentTag: "",
    frequency: "MONTHLY",
    assignedTechnician: "",
    startDate: nextMonthFirstDay(),
    estimatedDurationHours: "",
  };
}

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
const errorTextStyle = { color: colors.danger, fontSize: 12, margin: `${spacing.xs}px 0 0 0` };
const apiErrorStyle = {
  color: colors.danger,
  background: "rgba(239, 68, 68, 0.12)",
  border: `1px solid ${colors.danger}`,
  borderRadius: spacing.xs,
  padding: spacing.sm,
  marginBottom: spacing.sm,
};

function Field({ id, label, error, children }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <label htmlFor={id} style={labelStyle}>
        {label}
      </label>
      {children}
      {error ? (
        <p role="alert" style={errorTextStyle}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

// MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- initialEquipmentTag is optional
// and additive: every existing caller that omits it keeps the exact same
// blank-equipment behavior as before. Used by PM.jsx's "No active PM
// Schedule is available for this pump" flow to prefill the pump that was
// already being viewed, rather than requiring it to be retyped.
function initialFormFor(initialEquipmentTag) {
  return initialEquipmentTag ? { ...emptyForm(), equipmentTag: initialEquipmentTag } : emptyForm();
}

// AI5R-PHASE4E2, Section H -- required-field and duration validation, run
// client-side before the request is ever sent. `estimatedDurationHours`
// is only checked when non-blank (it is an optional field per Section B).
function validateForm(form) {
  const errors = {};
  if (!form.equipmentTag) {
    errors.equipmentTag = "Select a pump.";
  }
  if (!form.frequency) {
    errors.frequency = "Select a frequency.";
  }
  if (!form.startDate) {
    errors.startDate = "Select a start date.";
  }
  if (form.estimatedDurationHours !== "") {
    const duration = Number(form.estimatedDurationHours);
    if (!Number.isFinite(duration) || duration < 0) {
      errors.estimatedDurationHours = "Enter a duration of zero or more hours.";
    }
  }
  return errors;
}

// AI5R-PHASE4E2, Section H -- `errorMessage` is an optional, caller-owned
// string (PM.jsx's own createError state) shown for server-side failures
// (unknown pump, duplicate/conflict, API validation failure) that can
// only be known after a real submit attempt -- distinct from the
// client-side per-field errors above, which are known before any request
// is sent. See ai5rClient.js's formatApiErrorDetail() for why this string
// is now always human-readable instead of "[object Object],[object Object]".
export default function CreatePMScheduleModal({ isOpen, onClose, onCreate, initialEquipmentTag = "", errorMessage = null }) {
  const [form, setForm] = useState(() => initialFormFor(initialEquipmentTag));
  // AI5R-PHASE4E1, OWNER DECISION 6/7: PLANNED activities only -- this map
  // never feeds pm_occurrence.activities (PERFORMED activities) and is
  // reset independently of it; PMActivityFamilyChecklist itself carries no
  // "performed" semantics, so reusing it here for planning is safe.
  const [plannedMap, setPlannedMap] = useState({});
  const [fieldErrors, setFieldErrors] = useState({});

  const [pumps, setPumps] = useState([]);
  const [pumpsLoading, setPumpsLoading] = useState(false);
  const [pumpsError, setPumpsError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setForm(initialFormFor(initialEquipmentTag));
      setPlannedMap({});
      setFieldErrors({});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, initialEquipmentTag]);

  // AI5R-PHASE4E2, Section C -- pump master data, fetched fresh each time
  // the modal opens (same component-owns-its-fetch convention as
  // LTSAWorkspace's AssetLauncher). Never falls back to a free-text tag:
  // on failure the selector is simply unavailable with a visible error,
  // rather than inventing a pump tag the canonical registry never issued.
  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }
    let active = true;
    setPumpsLoading(true);
    setPumpsError(null);
    getPumps()
      .then((records) => records.map(mapPumpRecord))
      .then((mapped) => {
        if (active) {
          setPumps(mapped);
        }
      })
      .catch((error) => {
        if (active) {
          setPumpsError(error?.message || "Pumps could not be loaded.");
        }
      })
      .finally(() => {
        if (active) {
          setPumpsLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [isOpen]);

  function setField(name) {
    return (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  }

  function togglePlanned(code) {
    setPlannedMap((current) => ({ ...current, [code]: !current[code] }));
  }

  function handleSubmit(event) {
    event.preventDefault();

    const errors = validateForm(form);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }

    const plannedActivities = buildPlannedActivitiesPayload(plannedMap);
    onCreate({
      equipmentTag: form.equipmentTag,
      frequency: form.frequency,
      triggerType: deriveTriggerType(form.frequency),
      assignedTechnician: form.assignedTechnician,
      startDate: form.startDate,
      estimatedDurationHours: form.estimatedDurationHours === "" ? 0 : Number(form.estimatedDurationHours),
      notes: form.notes,
      plannedActivities: plannedActivities.length > 0 ? plannedActivities : null,
    });
    // AI5R-PHASE4E2 -- the form is deliberately NOT cleared here: on a
    // server-side failure (unknown pump, validation error, conflict) the
    // modal stays open (PM.jsx's handleCreate only closes it on success)
    // and the user's already-entered values must still be there. A
    // successful create closes the modal via the `isOpen` prop, and the
    // effect above re-initializes a fresh empty form the next time it
    // opens.
  }

  function handleClose() {
    setForm(emptyForm());
    setPlannedMap({});
    setFieldErrors({});
    onClose();
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create PM Schedule">
      {/* AI5R-PHASE4E2 -- noValidate: without it, the browser's own HTML5
          constraint validation (min="0" on Estimated Duration) silently
          blocks the submit event entirely for an out-of-range value,
          before validateForm() ever runs -- no submit event means no
          error message at all, an inconsistent, unstyled, browser-
          dependent failure mode. All validation now runs through
          validateForm() exclusively, so every failure gets the same
          styled, testable inline message. */}
      <form onSubmit={handleSubmit} noValidate>
        {errorMessage ? <p role="alert" style={apiErrorStyle}>{errorMessage}</p> : null}

        <div style={{ marginBottom: spacing.sm }}>
          {pumpsLoading ? (
            <p style={{ color: colors.textMuted, margin: 0 }}>Loading pumps...</p>
          ) : pumpsError ? (
            <p role="alert" style={errorTextStyle}>
              {pumpsError}
            </p>
          ) : (
            <AssetSelector
              id="pm-pump"
              label="Pump *"
              assets={pumps.map((pump) => ({ tag: pump.tag, name: pump.name }))}
              selectedTag={form.equipmentTag || null}
              onSelect={(tag) => setForm((current) => ({ ...current, equipmentTag: tag || "" }))}
            />
          )}
          {fieldErrors.equipmentTag ? (
            <p role="alert" style={errorTextStyle}>
              {fieldErrors.equipmentTag}
            </p>
          ) : null}
        </div>

        <Field id="pm-frequency" label="Frequency *" error={fieldErrors.frequency}>
          <select id="pm-frequency" style={fieldStyle} value={form.frequency} onChange={setField("frequency")}>
            {FREQUENCY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="pm-start-date" label="Start Date *" error={fieldErrors.startDate}>
          <input
            id="pm-start-date"
            type="date"
            style={fieldStyle}
            value={form.startDate}
            onChange={setField("startDate")}
          />
        </Field>

        <div style={{ marginBottom: spacing.sm }}>
          <div style={labelStyle}>Planned Activities</div>
          <PMActivityFamilyChecklist doneMap={plannedMap} onToggle={togglePlanned} />
        </div>

        <Field id="pm-technician" label="Assigned Technician">
          <input
            id="pm-technician"
            style={fieldStyle}
            value={form.assignedTechnician}
            onChange={setField("assignedTechnician")}
          />
        </Field>

        <Field id="pm-estimated-duration" label="Estimated Duration" error={fieldErrors.estimatedDurationHours}>
          <input
            id="pm-estimated-duration"
            type="number"
            min="0"
            step="0.25"
            style={fieldStyle}
            value={form.estimatedDurationHours}
            onChange={setField("estimatedDurationHours")}
          />
        </Field>

        <Field id="pm-notes" label="Notes">
          <input id="pm-notes" style={fieldStyle} value={form.notes} onChange={setField("notes")} />
        </Field>

        <div style={{ display: "flex", gap: spacing.sm, justifyContent: "flex-end", flexWrap: "wrap" }}>
          <Button type="button" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit">Create PM Schedule</Button>
        </div>
      </form>
    </Modal>
  );
}
