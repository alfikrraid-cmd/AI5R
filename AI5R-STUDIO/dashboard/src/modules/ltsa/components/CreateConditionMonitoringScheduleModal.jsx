import { useState } from "react";
import { Button, Modal } from "../../../design-system";

const EMPTY = { code: "", equipmentTag: "", monitoringType: "", measurementPoint: "", frequency: "", intervalUnit: "", effectiveDate: "" };

export default function CreateConditionMonitoringScheduleModal({ isOpen, onClose, onCreate }) {
  const [form, setForm] = useState(EMPTY);
  const set = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));
  function submit(event) {
    event.preventDefault();
    onCreate(form);
    setForm(EMPTY);
  }
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Condition Monitoring Schedule">
      <form onSubmit={submit}>
        {[["code", "Schedule Code"], ["equipmentTag", "Equipment"], ["monitoringType", "Monitoring Type"], ["measurementPoint", "Measurement Point"], ["frequency", "Frequency"], ["intervalUnit", "Interval Unit"], ["effectiveDate", "Effective Date"]].map(([field, label]) => (
          <label key={field} style={{ display: "block", marginBottom: 10 }}>{label}<input required={field === "code" || field === "equipmentTag" || field === "monitoringType"} type={field === "effectiveDate" ? "date" : "text"} value={form[field]} onChange={set(field)} style={{ display: "block", width: "100%" }} /></label>
        ))}
        <Button type="submit">Create Schedule</Button>
      </form>
    </Modal>
  );
}
