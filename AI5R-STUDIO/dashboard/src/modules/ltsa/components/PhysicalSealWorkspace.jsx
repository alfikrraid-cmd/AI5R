import { useEffect, useMemo, useState } from "react";
import { Button, EmptyState, Modal, Panel, StatusBadge, Table, Tabs } from "../../../design-system";
import { useOptionalAuth } from "../auth/AuthContext";
import { can } from "../auth/permissions";
import {
  createSealUnit,
  createSealUnitInspection,
  createSealUnitLifecycleEvent,
  createSealUnitRepair,
  createSealUnitWarrantyAssessment,
  decideSealWarrantyAssessment,
  getSealUnitHistory,
  getSealUnitInspections,
  getSealUnitInstallationReports,
  getSealUnitLifecycle,
  getSealUnitRepairs,
  getSealUnits,
  getSealUnitWarranty,
  linkInstallationReportToInstallEvent,
} from "../../../api/ai5rClient";

const COMPONENT_OPTIONS = [
  "SEAL_FACE", "MATING_RING", "O_RING", "SPRING", "GLAND", "SLEEVE", "DRIVE_COLLAR", "OTHER",
];

const EMPTY_FINDING = {
  component: "SEAL_FACE",
  condition: "",
  measurement_name: "",
  measured_value: "",
  unit: "",
  acceptance_min: "",
  acceptance_max: "",
  finding: "",
  action_required: "",
};

const EMPTY_LIFECYCLE = { event_type: "INSTALL", event_at: "", pump_tag_number: "", reason: "", notes: "", source_reference: "" };
const EMPTY_INSPECTION = {
  inspection_date: "", pump_tag_number: "", inspection_type: "GENERAL", overall_condition: "", failure_mode: "",
  root_cause: "", recommendation: "", disposition: "", inspected_by: "", notes: "", source_reference: "", findings: [EMPTY_FINDING],
};
const EMPTY_REPAIR = {
  repair_date: "", repair_type: "", repair_action: "", inspection_id: "", parts_replaced: "", repair_result: "", performed_by: "", notes: "", source_reference: "",
};
const EMPTY_LINK = { installation_code: "", installation_event_id: "", pump_tag_number: "", reason: "" };
const EMPTY_WARRANTY = { installation_event_id: "", claim_date: "", failure_date: "", inspection_id: "", source_reference: "" };
const EMPTY_DECISION = { assessment_id: "", decision: "PENDING_EXAMINATION", decision_reason: "", inspection_id: "" };
// MWO-LTSA-PHYSICAL-SEAL-001B -- registration only: no status, no
// current_pump_tag_number, no lifecycle/installation/warranty field --
// matches SealUnitRegisterRequest's own shape exactly, so there is
// nothing here a form could even attempt to smuggle as an implicit
// installation.
const EMPTY_REGISTER = { seal_code: "", serial_number: "" };

function valueOrNA(value) {
  if (value === null || value === undefined || value === "") return "N/A";
  return String(value);
}

function dateOnly(value) {
  return value ? String(value).slice(0, 10) : "N/A";
}

function omitEmpty(input) {
  return Object.fromEntries(Object.entries(input).filter(([, value]) => value !== "" && value !== null && value !== undefined));
}

function numberOrNull(value) {
  if (value === "") return null;
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function normalizeFinding(finding) {
  return {
    ...omitEmpty(finding),
    measured_value: numberOrNull(finding.measured_value),
    acceptance_min: numberOrNull(finding.acceptance_min),
    acceptance_max: numberOrNull(finding.acceptance_max),
  };
}

function eventPump(event) {
  return event?.pump_tag_number ?? event?.pumpTagNumber ?? event?.installation_pump_tag_number ?? null;
}

function eventDate(event) {
  return event?.event_at ?? event?.eventAt ?? event?.created_at ?? event?.inspection_date ?? event?.repair_date ?? null;
}

function statusTone(status) {
  const normalized = String(status ?? "").toUpperCase();
  if (["INSTALLED", "ACTIVE", "ACCEPTED", "WITHIN_WARRANTY_WINDOW"].includes(normalized)) return "active";
  if (["FAILED", "REJECTED", "SCRAPPED", "EXPIRED", "OUTSIDE_WARRANTY_WINDOW"].includes(normalized)) return "error";
  if (["UNDER_REPAIR", "PENDING_EXAMINATION", "WARNING"].includes(normalized)) return "warning";
  return "idle";
}

function allowedLifecycleEvents(status) {
  const normalized = String(status ?? "").toUpperCase();
  if (normalized === "INSTALLED") return ["REMOVE", "INSPECT", "SCRAP"];
  if (normalized === "UNDER_REPAIR") return ["REPAIR_COMPLETE", "SCRAP"];
  if (normalized === "SCRAPPED") return [];
  return ["INSTALL", "INSPECT", "REPAIR_START", "SCRAP"];
}

function ActionModal({ title, isOpen, onClose, children }) {
  return <Modal title={title} isOpen={isOpen} onClose={onClose}>{children}</Modal>;
}

function Field({ label, value, onChange, type = "text", required = false, as = "input", children }) {
  const Control = as;
  return (
    <label className="physical-seal-field">
      <span>{label}</span>
      <Control value={value} onChange={(event) => onChange(event.target.value)} type={type} required={required}>
        {children}
      </Control>
    </label>
  );
}

export default function PhysicalSealWorkspace({ sealTypes = [], units: unitsProp, onRefresh }) {
  const auth = useOptionalAuth();
  const canWrite = can(auth?.session, "seal.lifecycle_write");
  const [units, setUnits] = useState(unitsProp ?? []);
  const [loading, setLoading] = useState(unitsProp === undefined);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [activeTab, setActiveTab] = useState("lifecycle");
  const [detail, setDetail] = useState({ lifecycle: [], inspections: [], repairs: [], warranty: [], reports: [], history: [] });
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [modal, setModal] = useState(null);
  const [formError, setFormError] = useState(null);
  const [lifecycleForm, setLifecycleForm] = useState(EMPTY_LIFECYCLE);
  const [inspectionForm, setInspectionForm] = useState(EMPTY_INSPECTION);
  const [repairForm, setRepairForm] = useState(EMPTY_REPAIR);
  const [linkForm, setLinkForm] = useState(EMPTY_LINK);
  const [warrantyForm, setWarrantyForm] = useState(EMPTY_WARRANTY);
  const [decisionForm, setDecisionForm] = useState(EMPTY_DECISION);
  // MWO-LTSA-PHYSICAL-SEAL-001B -- separate from `modal`/`formError`
  // above: those are scoped to an already-selected unit's detail actions,
  // but registration must also be reachable from the zero-units empty
  // state below, where no unit is selected yet.
  const [registerOpen, setRegisterOpen] = useState(false);
  const [registerForm, setRegisterForm] = useState(EMPTY_REGISTER);
  const [registerError, setRegisterError] = useState(null);

  useEffect(() => {
    if (unitsProp !== undefined) {
      setUnits(unitsProp);
      return undefined;
    }
    let active = true;
    setLoading(true);
    getSealUnits()
      .then((records) => { if (active) { setUnits(records); setError(null); } })
      .catch((err) => { if (active) setError(err?.message || "Seal units could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [unitsProp]);

  const selectedUnit = useMemo(
    () => units.find((unit) => unit.seal_unit_id === selectedId) ?? units[0] ?? null,
    [units, selectedId]
  );

  useEffect(() => {
    if (!selectedUnit?.seal_unit_id) return undefined;
    if (selectedId !== selectedUnit.seal_unit_id) setSelectedId(selectedUnit.seal_unit_id);
    let active = true;
    setDetailLoading(true);
    Promise.all([
      getSealUnitLifecycle(selectedUnit.seal_unit_id),
      getSealUnitInspections(selectedUnit.seal_unit_id),
      getSealUnitRepairs(selectedUnit.seal_unit_id),
      getSealUnitWarranty(selectedUnit.seal_unit_id),
      getSealUnitInstallationReports(selectedUnit.seal_unit_id),
      getSealUnitHistory(selectedUnit.seal_unit_id),
    ]).then(([lifecycle, inspections, repairs, warranty, reports, history]) => {
      if (!active) return;
      setDetail({ lifecycle, inspections, repairs, warranty, reports, history });
      setDetailError(null);
    }).catch((err) => {
      if (active) setDetailError(err?.message || "Seal unit detail could not be loaded.");
    }).finally(() => { if (active) setDetailLoading(false); });
    return () => { active = false; };
  }, [selectedUnit?.seal_unit_id, selectedId]);

  const selectedSealType = useMemo(
    () => sealTypes.find((seal) => seal.code === selectedUnit?.seal_code || seal.seal_code === selectedUnit?.seal_code) ?? null,
    [sealTypes, selectedUnit]
  );
  const installEvents = detail.lifecycle.filter((event) => String(event.event_type).toUpperCase() === "INSTALL");

  async function refreshDetail() {
    if (unitsProp === undefined) setUnits(await getSealUnits());
    onRefresh?.();
  }

  function openModal(name) {
    setFormError(null);
    setModal(name);
  }

  async function submitRegister(event) {
    event.preventDefault();
    setRegisterError(null);
    try {
      await createSealUnit(omitEmpty(registerForm));
      setRegisterOpen(false);
      setRegisterForm(EMPTY_REGISTER);
      if (unitsProp === undefined) setUnits(await getSealUnits());
      onRefresh?.();
    } catch (err) {
      setRegisterError(err?.message || "Backend rejected the registration.");
    }
  }

  const registerModal = (
    <ActionModal title="Register Physical Seal" isOpen={registerOpen} onClose={() => setRegisterOpen(false)}>
      <form onSubmit={submitRegister}>
        <Field label="Seal Type" value={registerForm.seal_code} as="select" required onChange={(value) => setRegisterForm({ ...registerForm, seal_code: value })}>
          <option value="">Select seal type</option>
          {sealTypes.map((seal) => { const code = seal.seal_code ?? seal.code; return <option key={code} value={code}>{code}{seal.name ? ` - ${seal.name}` : ""}</option>; })}
        </Field>
        <Field label="Serial Number (optional)" value={registerForm.serial_number} onChange={(value) => setRegisterForm({ ...registerForm, serial_number: value })} />
        <p>Registration only. This does not install the seal on a pump, start a warranty period, or create a lifecycle event.</p>
        {registerError ? <p role="alert">{registerError}</p> : null}
        <Button type="submit">Register</Button>
      </form>
    </ActionModal>
  );

  async function submit(action) {
    if (!selectedUnit) return;
    setFormError(null);
    try {
      await action();
      setModal(null);
      await refreshDetail();
      const id = selectedUnit.seal_unit_id;
      const [lifecycle, inspections, repairs, warranty, reports, history] = await Promise.all([
        getSealUnitLifecycle(id), getSealUnitInspections(id), getSealUnitRepairs(id), getSealUnitWarranty(id), getSealUnitInstallationReports(id), getSealUnitHistory(id),
      ]);
      setDetail({ lifecycle, inspections, repairs, warranty, reports, history });
    } catch (err) {
      setFormError(err?.message || "Backend rejected the operation.");
    }
  }

  const columns = [
    { key: "seal_unit_id", header: "Seal Unit", render: (value) => value },
    { key: "seal_code", header: "Seal Type", render: (value) => value },
    { key: "serial_number", header: "Serial", render: (value) => valueOrNA(value) },
    { key: "status", header: "Status", render: (value) => valueOrNA(value) },
    { key: "current_pump_tag_number", header: "Current Pump", render: (value) => valueOrNA(value) },
  ];

  if (loading) return <Panel><p>Loading physical seal units...</p></Panel>;
  if (error) return <Panel><p role="alert">{error}</p></Panel>;
  if (units.length === 0) {
    return (
      <section aria-label="Physical Seal Workspace">
        <EmptyState title="No physical seal units" description="Seal type catalog data is available, but no seal_unit records were returned." />
        <div className="physical-seal-actions" aria-label="Seal unit actions">
          <Button disabled={!canWrite} onClick={() => setRegisterOpen(true)}>Register Physical Seal</Button>
          {!canWrite ? <p className="physical-seal-readonly">Read-only: seal.lifecycle_write is required to register a physical seal.</p> : null}
        </div>
        {registerModal}
      </section>
    );
  }

  return (
    <section className="physical-seal-workspace" aria-label="Physical Seal Workspace">
      <Panel>
        <div className="physical-seal-kicker">PHYSICAL SEAL WORKSPACE</div>
        <div className="physical-seal-grid">
          <div>
            <h2>{valueOrNA(selectedUnit?.seal_unit_id)}</h2>
            <p>Seal Type: {valueOrNA(selectedUnit?.seal_code)}{selectedSealType?.name ? ` / ${selectedSealType.name}` : ""}</p>
            <p>Serial Number: {valueOrNA(selectedUnit?.serial_number)}</p>
          </div>
          <StatusBadge label="Current State" status={valueOrNA(selectedUnit?.status)} />
          <div>
            <p>Current Pump: {valueOrNA(selectedUnit?.current_pump_tag_number)}</p>
            <p>Created: {dateOnly(selectedUnit?.created_at)} | Updated: {dateOnly(selectedUnit?.updated_at)}</p>
          </div>
        </div>
      </Panel>

      <div className="physical-seal-table-wrap">
        <Table columns={columns} data={units} rowKey="seal_unit_id" selectedKey={selectedUnit?.seal_unit_id} onRowClick={(unit) => setSelectedId(unit.seal_unit_id)} />
      </div>

      <div className="physical-seal-actions" aria-label="Seal unit actions">
        <Button disabled={!canWrite} onClick={() => setRegisterOpen(true)}>Register Physical Seal</Button>
        <Button disabled={!canWrite || allowedLifecycleEvents(selectedUnit?.status).length === 0} onClick={() => openModal("lifecycle")}>Lifecycle Action</Button>
        <Button disabled={!canWrite} onClick={() => openModal("inspection")}>Add Inspection</Button>
        <Button disabled={!canWrite} onClick={() => openModal("repair")}>Add Repair</Button>
        <Button disabled={!canWrite || installEvents.length === 0} onClick={() => openModal("installation")}>Link Installation Report</Button>
        <Button disabled={!canWrite || installEvents.length === 0} onClick={() => openModal("warranty")}>Assess Warranty</Button>
        {!canWrite ? <p className="physical-seal-readonly">Read-only: seal.lifecycle_write is required for append actions.</p> : null}
      </div>

      {detailLoading ? <Panel><p>Loading seal unit history...</p></Panel> : null}
      {detailError ? <Panel><p role="alert">{detailError}</p></Panel> : null}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: "lifecycle", label: "Lifecycle" }, { key: "inspection", label: "Inspection" }, { key: "repair", label: "Repair" },
          { key: "installation", label: "Installation" }, { key: "warranty", label: "Warranty" }, { key: "history", label: "History" },
        ]}
      />

      {activeTab === "lifecycle" ? (
        <Panel><h3>Lifecycle Ledger</h3>{detail.lifecycle.length ? detail.lifecycle.map((event) => <p key={event.event_id}>{dateOnly(eventDate(event))} - {event.event_type} - Pump {valueOrNA(eventPump(event))} - {valueOrNA(event.reason)}</p>) : <p>No lifecycle events recorded.</p>}</Panel>
      ) : null}
      {activeTab === "inspection" ? (
        <Panel><h3>Inspection</h3>{detail.inspections.length ? detail.inspections.map((item) => <p key={item.inspection_id}>{dateOnly(item.inspection_date)} - {item.inspection_type} - {valueOrNA(item.overall_condition)} - Findings: {item.findings?.length ?? 0}</p>) : <p>No inspections recorded.</p>}</Panel>
      ) : null}
      {activeTab === "repair" ? (
        <Panel><h3>Repair</h3>{detail.repairs.length ? detail.repairs.map((item) => <p key={item.repair_id}>{dateOnly(item.repair_date)} - {item.repair_type} - {item.repair_result} - Inspection {valueOrNA(item.inspection_id)}</p>) : <p>No repairs recorded.</p>}</Panel>
      ) : null}
      {activeTab === "installation" ? (
        <Panel><h3>Installation Reports</h3>{detail.reports.length ? detail.reports.map((item) => <p key={item.installation_code}>{item.installation_code} - Report Date {dateOnly(item.report_date)} - Install Event {valueOrNA(item.installation_event_id)}</p>) : <p>No linked installation reports.</p>}<p>Install event date is the authoritative fitment date; report date is metadata.</p></Panel>
      ) : null}
      {activeTab === "warranty" ? (
        <Panel><h3>Warranty</h3><p>KAK rule: warranty period is 18 calendar months from actual installation date.</p>{detail.warranty.length ? detail.warranty.map((item) => <div key={item.assessment_id} className="physical-seal-row"><span>Installation Date {dateOnly(item.installation_date)}</span><span>Warranty End {dateOnly(item.warranty_end)}</span><StatusBadge label="Window Status" status={valueOrNA(item.window_status)} /><StatusBadge label="Claim Decision" status={valueOrNA(item.claim_decision ?? item.decision)} /></div>) : <p>No warranty assessments recorded.</p>}</Panel>
      ) : null}
      {activeTab === "history" ? (
        <Panel><h3>Equipment History</h3>{detail.history.length ? detail.history.map((item, index) => <p key={item.history_id ?? `${item.event_type}-${index}`}>{dateOnly(item.occurred_at ?? item.event_at)} - {item.event_type ?? item.record_type} - Pump {valueOrNA(eventPump(item))}</p>) : <p>No seal history records.</p>}</Panel>
      ) : null}

      <ActionModal title="Lifecycle Action" isOpen={modal === "lifecycle"} onClose={() => setModal(null)}>
        <form onSubmit={(event) => { event.preventDefault(); submit(() => createSealUnitLifecycleEvent(selectedUnit.seal_unit_id, omitEmpty(lifecycleForm))); }}>
          <Field label="Action" value={lifecycleForm.event_type} onChange={(value) => setLifecycleForm({ ...lifecycleForm, event_type: value })} as="select">{allowedLifecycleEvents(selectedUnit?.status).map((action) => <option key={action}>{action}</option>)}</Field>
          <Field label="Event Date" type="datetime-local" required value={lifecycleForm.event_at} onChange={(value) => setLifecycleForm({ ...lifecycleForm, event_at: value })} />
          <Field label="Pump Tag" value={lifecycleForm.pump_tag_number} onChange={(value) => setLifecycleForm({ ...lifecycleForm, pump_tag_number: value })} />
          <Field label="Reason" value={lifecycleForm.reason} onChange={(value) => setLifecycleForm({ ...lifecycleForm, reason: value })} />
          <Field label="Notes" value={lifecycleForm.notes} onChange={(value) => setLifecycleForm({ ...lifecycleForm, notes: value })} />
          <Field label="Source Reference" value={lifecycleForm.source_reference} onChange={(value) => setLifecycleForm({ ...lifecycleForm, source_reference: value })} />
          {formError ? <p role="alert">{formError}</p> : null}<Button type="submit">Submit</Button>
        </form>
      </ActionModal>

      <ActionModal title="Add Inspection" isOpen={modal === "inspection"} onClose={() => setModal(null)}>
        <form onSubmit={(event) => { event.preventDefault(); submit(() => createSealUnitInspection(selectedUnit.seal_unit_id, { ...omitEmpty(inspectionForm), findings: inspectionForm.findings.map(normalizeFinding) })); }}>
          <Field label="Inspection Date" type="datetime-local" required value={inspectionForm.inspection_date} onChange={(value) => setInspectionForm({ ...inspectionForm, inspection_date: value })} />
          <Field label="Pump Tag" value={inspectionForm.pump_tag_number} onChange={(value) => setInspectionForm({ ...inspectionForm, pump_tag_number: value })} />
          <Field label="Inspection Type" value={inspectionForm.inspection_type} onChange={(value) => setInspectionForm({ ...inspectionForm, inspection_type: value })} />
          <Field label="Overall Condition" value={inspectionForm.overall_condition} onChange={(value) => setInspectionForm({ ...inspectionForm, overall_condition: value })} />
          <Field label="Failure Mode" value={inspectionForm.failure_mode} onChange={(value) => setInspectionForm({ ...inspectionForm, failure_mode: value })} />
          <Field label="Root Cause" value={inspectionForm.root_cause} onChange={(value) => setInspectionForm({ ...inspectionForm, root_cause: value })} />
          <Field label="Recommendation" value={inspectionForm.recommendation} onChange={(value) => setInspectionForm({ ...inspectionForm, recommendation: value })} />
          <Field label="Disposition" value={inspectionForm.disposition} onChange={(value) => setInspectionForm({ ...inspectionForm, disposition: value })} />
          <Field label="Inspected By" value={inspectionForm.inspected_by} onChange={(value) => setInspectionForm({ ...inspectionForm, inspected_by: value })} />
          {inspectionForm.findings.map((finding, index) => <div className="physical-seal-finding" key={index}><Field label="Component" value={finding.component} as="select" onChange={(value) => { const next = [...inspectionForm.findings]; next[index] = { ...finding, component: value }; setInspectionForm({ ...inspectionForm, findings: next }); }}>{COMPONENT_OPTIONS.map((component) => <option key={component}>{component}</option>)}</Field><Field label="Measured Value" value={finding.measured_value} onChange={(value) => { const next = [...inspectionForm.findings]; next[index] = { ...finding, measured_value: value }; setInspectionForm({ ...inspectionForm, findings: next }); }} /><Field label="Finding" value={finding.finding} onChange={(value) => { const next = [...inspectionForm.findings]; next[index] = { ...finding, finding: value }; setInspectionForm({ ...inspectionForm, findings: next }); }} /></div>)}
          <Button onClick={() => setInspectionForm({ ...inspectionForm, findings: [...inspectionForm.findings, EMPTY_FINDING] })}>Add Finding Row</Button>
          {formError ? <p role="alert">{formError}</p> : null}<Button type="submit">Submit</Button>
        </form>
      </ActionModal>

      <ActionModal title="Add Repair" isOpen={modal === "repair"} onClose={() => setModal(null)}>
        <form onSubmit={(event) => { event.preventDefault(); submit(() => createSealUnitRepair(selectedUnit.seal_unit_id, { ...omitEmpty(repairForm), inspection_id: repairForm.inspection_id || null, parts_replaced: repairForm.parts_replaced ? JSON.parse(repairForm.parts_replaced) : [] })); }}>
          <Field label="Repair Date" type="datetime-local" required value={repairForm.repair_date} onChange={(value) => setRepairForm({ ...repairForm, repair_date: value })} />
          <Field label="Repair Type" value={repairForm.repair_type} onChange={(value) => setRepairForm({ ...repairForm, repair_type: value })} />
          <Field label="Repair Action" value={repairForm.repair_action} onChange={(value) => setRepairForm({ ...repairForm, repair_action: value })} />
          <Field label="Linked Inspection" value={repairForm.inspection_id} as="select" onChange={(value) => setRepairForm({ ...repairForm, inspection_id: value })}><option value="">N/A</option>{detail.inspections.map((item) => <option key={item.inspection_id} value={item.inspection_id}>{item.inspection_id}</option>)}</Field>
          <Field label="Parts Replaced JSON" value={repairForm.parts_replaced} onChange={(value) => setRepairForm({ ...repairForm, parts_replaced: value })} />
          <Field label="Repair Result" value={repairForm.repair_result} onChange={(value) => setRepairForm({ ...repairForm, repair_result: value })} />
          <Field label="Performed By" value={repairForm.performed_by} onChange={(value) => setRepairForm({ ...repairForm, performed_by: value })} />
          {formError ? <p role="alert">{formError}</p> : null}<Button type="submit">Submit</Button>
        </form>
      </ActionModal>

      <ActionModal title="Link Installation Report" isOpen={modal === "installation"} onClose={() => setModal(null)}>
        <form onSubmit={(event) => { event.preventDefault(); submit(() => linkInstallationReportToInstallEvent(linkForm.installation_code, omitEmpty({ seal_unit_id: selectedUnit.seal_unit_id, installation_event_id: linkForm.installation_event_id, pump_tag_number: linkForm.pump_tag_number, reason: linkForm.reason }))); }}>
          <Field label="Installation Report" value={linkForm.installation_code} as="select" required onChange={(value) => setLinkForm({ ...linkForm, installation_code: value })}><option value="">Select report</option>{detail.reports.map((item) => <option key={item.installation_code}>{item.installation_code}</option>)}</Field>
          <Field label="INSTALL Event" value={linkForm.installation_event_id} as="select" required onChange={(value) => setLinkForm({ ...linkForm, installation_event_id: value })}><option value="">Select install event</option>{installEvents.map((event) => <option key={event.event_id} value={event.event_id}>{event.event_id} - {dateOnly(event.event_at)}</option>)}</Field>
          <Field label="Pump Tag" value={linkForm.pump_tag_number} onChange={(value) => setLinkForm({ ...linkForm, pump_tag_number: value })} />
          <Field label="Reason" value={linkForm.reason} onChange={(value) => setLinkForm({ ...linkForm, reason: value })} />
          {formError ? <p role="alert">{formError}</p> : null}<Button type="submit">Submit</Button>
        </form>
      </ActionModal>

      <ActionModal title="Assess Warranty" isOpen={modal === "warranty"} onClose={() => setModal(null)}>
        <form onSubmit={(event) => { event.preventDefault(); submit(() => createSealUnitWarrantyAssessment(selectedUnit.seal_unit_id, omitEmpty(warrantyForm))); }}>
          <Field label="INSTALL Event" value={warrantyForm.installation_event_id} as="select" required onChange={(value) => setWarrantyForm({ ...warrantyForm, installation_event_id: value })}><option value="">Select install event</option>{installEvents.map((event) => <option key={event.event_id} value={event.event_id}>{event.event_id} - {dateOnly(event.event_at)}</option>)}</Field>
          <Field label="Claim Date" type="date" value={warrantyForm.claim_date} onChange={(value) => setWarrantyForm({ ...warrantyForm, claim_date: value })} />
          <Field label="Failure Date" type="date" value={warrantyForm.failure_date} onChange={(value) => setWarrantyForm({ ...warrantyForm, failure_date: value })} />
          <Field label="Inspection" value={warrantyForm.inspection_id} as="select" onChange={(value) => setWarrantyForm({ ...warrantyForm, inspection_id: value })}><option value="">N/A</option>{detail.inspections.map((item) => <option key={item.inspection_id} value={item.inspection_id}>{item.inspection_id}</option>)}</Field>
          {formError ? <p role="alert">{formError}</p> : null}<Button type="submit">Create PENDING_EXAMINATION</Button>
        </form>
        <form onSubmit={(event) => { event.preventDefault(); submit(() => decideSealWarrantyAssessment(decisionForm.assessment_id, omitEmpty({ decision: decisionForm.decision, decision_reason: decisionForm.decision_reason, inspection_id: decisionForm.inspection_id }))); }}>
          <Field label="Assessment" value={decisionForm.assessment_id} as="select" onChange={(value) => setDecisionForm({ ...decisionForm, assessment_id: value })}><option value="">Select assessment</option>{detail.warranty.map((item) => <option key={item.assessment_id}>{item.assessment_id}</option>)}</Field>
          <Field label="Decision" value={decisionForm.decision} as="select" onChange={(value) => setDecisionForm({ ...decisionForm, decision: value })}>{["ACCEPTED", "REJECTED", "NOT_APPLICABLE"].map((item) => <option key={item}>{item}</option>)}</Field>
          <Field label="Decision Reason" value={decisionForm.decision_reason} onChange={(value) => setDecisionForm({ ...decisionForm, decision_reason: value })} />
          <Field label="Inspection" value={decisionForm.inspection_id} as="select" onChange={(value) => setDecisionForm({ ...decisionForm, inspection_id: value })}><option value="">N/A</option>{detail.inspections.map((item) => <option key={item.inspection_id} value={item.inspection_id}>{item.inspection_id}</option>)}</Field>
          {formError ? <p role="alert">{formError}</p> : null}<Button type="submit">Record Decision</Button>
        </form>
      </ActionModal>

      {registerModal}
    </section>
  );
}