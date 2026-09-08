import { useEffect, useRef, useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { emptyMeasurementFormValues, buildMeasurementsPayload } from "../utils/conditionMonitoringMeasurementFields";
import ConditionMonitoringMeasurementFieldsForm, { fieldStyle, labelStyle, Field } from "./ConditionMonitoringMeasurementFieldsForm";
import AssetSelector from "./AssetSelector";
import { getPumps } from "../../../api/ai5rClient";
import { mapPumpRecord } from "../utils/pumpMapping";

// AI5R-CMON-UX-001 -- persistent equipment context (Gate 3): once a pump
// is selected, its tag stays the strongest visual element on screen
// instead of being buried in a dropdown's current value. Only ever shows
// metadata this component actually received from the canonical pump
// source (getPumps() -> mapPumpRecord()) -- `area`/`name` are omitted
// entirely, never fabricated as blank/placeholder text, when a given
// pump's record doesn't have them.
function SelectedEquipmentCard({ pump, onChange }) {
  return (
    <div
      data-testid="cmon-selected-equipment-card"
      style={{
        border: `1px solid ${colors.border}`,
        borderRadius: spacing.xs,
        padding: spacing.sm,
        marginBottom: spacing.md,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: spacing.sm,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 11, color: colors.textMuted, textTransform: "uppercase", letterSpacing: 0.5 }}>
          Selected Equipment
        </div>
        <div style={{ fontSize: 22, fontWeight: 700, color: colors.text, wordBreak: "break-word" }}>{pump.tag}</div>
        {pump.name && <div style={{ fontSize: 13, color: colors.textMuted }}>{pump.name}</div>}
        {pump.area && <div style={{ fontSize: 12, color: colors.textMuted }}>Area {pump.area}</div>}
      </div>
      <Button type="button" onClick={onChange}>
        Change
      </Button>
    </div>
  );
}

// MWO-LTSA-CMON-ADHOC-ENTRY-001 -- the "+ Add Reading" flow: a Condition
// Monitoring reading with NO schedule requirement at all, for the real
// gap Phase 4F.1 found -- CreateConditionMonitoringReadingModal.jsx
// (unchanged, still used wherever a real schedule already exists) only
// offers a dropdown of existing schedules and dead-ends when a pump has
// none. This is a SEPARATE, additive modal, not a redesign of that one:
// same shared measurement form/catalog (ConditionMonitoringMeasurement
// FieldsForm, conditionMonitoringMeasurementFields.js), same canonical
// pump source (AssetSelector + getPumps(), reused verbatim from
// AI5R-PHASE4E2, never modified), same null-coercion/tri-state-leak
// discipline. No schedule/reading-code/provenance/workflow-status/
// created-by field is ever shown -- those are entirely server-controlled
// (routers/condition_monitoring.py's create_ad_hoc_ltsa_condition_
// monitoring_reading, MANUAL provenance always hardcoded server-side).
export default function CreateAdHocConditionMonitoringReadingModal({ isOpen, onClose, onCreate, onSaved }) {
  const [pumps, setPumps] = useState([]);
  const [pumpsError, setPumpsError] = useState(null);
  const [assetCode, setAssetCode] = useState(null);
  // AI5R-CMON-UX-001 -- when true, show the equipment selector even
  // though a pump is already chosen (the "Change" action from the
  // equipment card). Distinct from assetCode itself so re-selecting the
  // SAME pump still returns to the card, and so the card/selector swap
  // never touches already-entered measurement values.
  const [changingEquipment, setChangingEquipment] = useState(false);
  const [readingDate, setReadingDate] = useState("");
  const [finding, setFinding] = useState("");
  const [measurements, setMeasurements] = useState(emptyMeasurementFormValues());
  // AI5R-CMON-UX-PHASE1B -- pending state for the two explicit save
  // actions below. `savingRef` (checked/set synchronously, before any
  // React re-render) is the actual double-submit guard; `isSaving` only
  // drives the disabled UI, since state updates are not synchronous.
  const [isSaving, setIsSaving] = useState(false);
  const savingRef = useRef(false);
  const formRef = useRef(null);
  // Bumped after a successful Save & Add Another so a focus effect can
  // move focus into the (now-cleared) measurement form without having to
  // reach into ConditionMonitoringMeasurementFieldsForm's own state.
  const [addAnotherFocusToken, setAddAnotherFocusToken] = useState(0);

  useEffect(() => {
    if (addAnotherFocusToken === 0) {
      return;
    }
    formRef.current?.querySelector("[aria-expanded]")?.focus();
  }, [addAnotherFocusToken]);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }
    let active = true;
    getPumps()
      .then((records) => records.map(mapPumpRecord))
      .then((mapped) => {
        if (active) {
          // Only the fields the Selected Equipment card can honestly show
          // are kept -- never more than the canonical source provides,
          // never less than AssetSelector itself needs (tag/name).
          setPumps(mapped.map((pump) => ({ tag: pump.tag, name: pump.name, area: pump.area })));
        }
      })
      .catch((error) => {
        if (active) {
          setPumpsError(error.message || "Failed to load pumps");
        }
      });
    return () => {
      active = false;
    };
  }, [isOpen]);

  const selectedPump = pumps.find((pump) => pump.tag === assetCode) ?? null;
  const showSelector = !selectedPump || changingEquipment;

  function setMeasurementField(name) {
    return (event) => setMeasurements((current) => ({ ...current, [name]: event.target.value }));
  }

  function resetForm() {
    setAssetCode(null);
    setChangingEquipment(false);
    setReadingDate("");
    setFinding("");
    setMeasurements(emptyMeasurementFormValues());
  }

  function handleSelectPump(tag) {
    setAssetCode(tag);
    setChangingEquipment(false);
  }

  // AI5R-CMON-UX-PHASE1B -- the one place either save action reaches the
  // canonical create call. `onCreate` (ConditionMonitoring.jsx's
  // handleCreateAdHocReading) stays the ONLY place that performs the real
  // API request and returns the created record on success / rejects on
  // failure; this modal never guesses at success, and never resets any
  // entered value until that promise has actually resolved.
  async function submit(addAnother) {
    if (!assetCode || !readingDate || savingRef.current) {
      return;
    }

    savingRef.current = true;
    setIsSaving(true);
    try {
      const created = await onCreate({
        assetCode,
        readingDate,
        finding: finding.trim() ? finding.trim() : null,
        measurements: buildMeasurementsPayload(measurements),
      });

      if (addAnother) {
        // Save & Add Another: keep the pump, equipment card, and reading
        // date -- only the per-reading fields are cleared.
        setFinding("");
        setMeasurements(emptyMeasurementFormValues());
        setAddAnotherFocusToken((token) => token + 1);
      } else {
        resetForm();
        onSaved?.(created);
      }
    } catch {
      // Failure is already surfaced through the parent's existing error
      // path (createError, via onCreate's rejection); this modal's job on
      // failure is only to change nothing -- pump, date, measurements and
      // notes all stay exactly as entered, and the modal stays open.
    } finally {
      savingRef.current = false;
      setIsSaving(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    submit(false);
  }

  function handleSaveAndAddAnother() {
    submit(true);
  }

  function handleClose() {
    resetForm();
    onClose();
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Add Condition Monitoring Reading">
      <form onSubmit={handleSubmit} ref={formRef}>
        {pumpsError ? <p role="alert">{pumpsError}</p> : null}

        {showSelector ? (
          <AssetSelector
            assets={pumps}
            selectedTag={assetCode}
            onSelect={handleSelectPump}
            label="Pump"
            id="cmon-adhoc-pump"
            autoFocus={changingEquipment}
          />
        ) : (
          <SelectedEquipmentCard pump={selectedPump} onChange={() => setChangingEquipment(true)} />
        )}

        <Field id="cmon-adhoc-reading-date" label="Reading Date">
          <input
            id="cmon-adhoc-reading-date"
            type="date"
            style={fieldStyle}
            value={readingDate}
            onChange={(event) => setReadingDate(event.target.value)}
            required
          />
        </Field>

        <ConditionMonitoringMeasurementFieldsForm measurements={measurements} onFieldChange={setMeasurementField} idPrefix="cmon-adhoc" />

        <Field id="cmon-adhoc-finding" label="Finding / Notes">
          <textarea
            id="cmon-adhoc-finding"
            style={{ ...fieldStyle, minHeight: 60, resize: "vertical" }}
            value={finding}
            onChange={(event) => setFinding(event.target.value)}
          />
        </Field>

        <div style={{ display: "flex", gap: spacing.sm, justifyContent: "flex-end" }}>
          <Button type="button" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSaveAndAddAnother} disabled={!assetCode || !readingDate || isSaving}>
            Save & Add Another
          </Button>
          <Button type="submit" disabled={!assetCode || !readingDate || isSaving}>
            Save Reading
          </Button>
        </div>
      </form>
    </Modal>
  );
}
