import { useEffect, useState } from "react";
import { Button, Modal } from "../../../design-system";
import spacing from "../../../design-system/theme/spacing";
import { emptyMeasurementFormValues, buildMeasurementsPayload } from "../utils/conditionMonitoringMeasurementFields";
import ConditionMonitoringMeasurementFieldsForm, { fieldStyle, labelStyle, Field } from "./ConditionMonitoringMeasurementFieldsForm";
import AssetSelector from "./AssetSelector";
import { getPumps } from "../../../api/ai5rClient";
import { mapPumpRecord } from "../utils/pumpMapping";

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
export default function CreateAdHocConditionMonitoringReadingModal({ isOpen, onClose, onCreate }) {
  const [pumps, setPumps] = useState([]);
  const [pumpsError, setPumpsError] = useState(null);
  const [assetCode, setAssetCode] = useState(null);
  const [readingDate, setReadingDate] = useState("");
  const [finding, setFinding] = useState("");
  const [measurements, setMeasurements] = useState(emptyMeasurementFormValues());

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }
    let active = true;
    getPumps()
      .then((records) => records.map(mapPumpRecord))
      .then((mapped) => {
        if (active) {
          setPumps(mapped.map((pump) => ({ tag: pump.tag, name: pump.name })));
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

  function setMeasurementField(name) {
    return (event) => setMeasurements((current) => ({ ...current, [name]: event.target.value }));
  }

  function resetForm() {
    setAssetCode(null);
    setReadingDate("");
    setFinding("");
    setMeasurements(emptyMeasurementFormValues());
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (!assetCode || !readingDate) {
      return;
    }

    onCreate({
      assetCode,
      readingDate,
      finding: finding.trim() ? finding.trim() : null,
      measurements: buildMeasurementsPayload(measurements),
    });
    resetForm();
  }

  function handleClose() {
    resetForm();
    onClose();
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Add Condition Monitoring Reading">
      <form onSubmit={handleSubmit}>
        {pumpsError ? <p role="alert">{pumpsError}</p> : null}

        <AssetSelector assets={pumps} selectedTag={assetCode} onSelect={setAssetCode} label="Pump" id="cmon-adhoc-pump" />

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
          <Button type="submit" disabled={!assetCode || !readingDate}>
            Save Draft
          </Button>
        </div>
      </form>
    </Modal>
  );
}
