import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PhysicalSealWorkspace from "./PhysicalSealWorkspace";
import * as api from "../../../api/ai5rClient";
import { useOptionalAuth } from "../auth/AuthContext";

vi.mock("../auth/AuthContext", () => ({ useOptionalAuth: vi.fn() }));
vi.mock("../../../api/ai5rClient", () => ({
  createSealUnitInspection: vi.fn(),
  createSealUnitLifecycleEvent: vi.fn(),
  createSealUnitRepair: vi.fn(),
  createSealUnitWarrantyAssessment: vi.fn(),
  decideSealWarrantyAssessment: vi.fn(),
  getSealUnitHistory: vi.fn(),
  getSealUnitInspections: vi.fn(),
  getSealUnitInstallationReports: vi.fn(),
  getSealUnitLifecycle: vi.fn(),
  getSealUnitRepairs: vi.fn(),
  getSealUnits: vi.fn(),
  getSealUnitWarranty: vi.fn(),
  linkInstallationReportToInstallEvent: vi.fn(),
}));

const UNIT_ID = "11111111-1111-4111-8111-111111111111";
const OTHER_UNIT_ID = "22222222-2222-4222-8222-222222222222";
const units = [
  { seal_unit_id: UNIT_ID, seal_code: "TYPE-A", serial_number: null, status: "INSTALLED", current_pump_tag_number: "110-P-9A", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-02-01T00:00:00Z" },
  { seal_unit_id: OTHER_UNIT_ID, seal_code: "TYPE-B", serial_number: "SN-2", status: "SPARE", current_pump_tag_number: null },
];
const lifecycle = [
  { event_id: "evt-install", seal_unit_id: UNIT_ID, event_type: "INSTALL", event_at: "2026-01-10T00:00:00Z", pump_tag_number: "110-P-9A", reason: "fitment" },
  { event_id: "evt-remove", seal_unit_id: UNIT_ID, event_type: "REMOVE", event_at: "2026-03-01T00:00:00Z", pump_tag_number: "110-P-9A", reason: "planned" },
];
const inspections = [{ inspection_id: "insp-1", inspection_date: "2026-03-02T00:00:00Z", inspection_type: "FAILURE", overall_condition: "WORN", findings: [{ component: "SEAL_FACE" }] }];
const repairs = [{ repair_id: "rep-1", repair_date: "2026-03-03T00:00:00Z", repair_type: "SHOP", repair_result: "SCRAPPED", inspection_id: "insp-1" }];
const reports = [{ installation_code: "IR-1", report_date: "2026-01-20T00:00:00Z", installation_event_id: null }];
const warranty = [{ assessment_id: "wa-1", installation_date: "2026-01-10T00:00:00Z", warranty_end: "2027-07-10T00:00:00Z", window_status: "WITHIN_WARRANTY_WINDOW", claim_decision: "PENDING_EXAMINATION" }];
const history = [
  { history_id: "h1", record_type: "INSTALL", occurred_at: "2026-01-10T00:00:00Z", pump_tag_number: "110-P-9A" },
  { history_id: "h2", record_type: "INSPECTION", occurred_at: "2026-03-02T00:00:00Z", pump_tag_number: null },
  { history_id: "h3", record_type: "INSTALL", occurred_at: "2026-04-01T00:00:00Z", pump_tag_number: "211-P-1A" },
];

function mockDetail() {
  api.getSealUnitLifecycle.mockResolvedValue(lifecycle);
  api.getSealUnitInspections.mockResolvedValue(inspections);
  api.getSealUnitRepairs.mockResolvedValue(repairs);
  api.getSealUnitWarranty.mockResolvedValue(warranty);
  api.getSealUnitInstallationReports.mockResolvedValue(reports);
  api.getSealUnitHistory.mockResolvedValue(history);
}

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  vi.clearAllMocks();
  useOptionalAuth.mockReturnValue({ session: { permissions: ["seal.read", "seal.lifecycle_write"] } });
  api.getSealUnits.mockResolvedValue(units);
  mockDetail();
  api.createSealUnitLifecycleEvent.mockResolvedValue({ data: { event_id: "evt-new" } });
  api.createSealUnitInspection.mockResolvedValue({ data: { inspection_id: "insp-new" } });
  api.createSealUnitRepair.mockResolvedValue({ data: { repair_id: "rep-new" } });
  api.linkInstallationReportToInstallEvent.mockResolvedValue({ data: { installation_code: "IR-1" } });
  api.createSealUnitWarrantyAssessment.mockResolvedValue({ data: { assessment_id: "wa-new" } });
  api.decideSealWarrantyAssessment.mockResolvedValue({ data: { assessment_id: "wa-1" } });
});

describe("PhysicalSealWorkspace", () => {
  it("loads physical seal units while preserving the Seal Type catalog distinction", async () => {
    render(<PhysicalSealWorkspace sealTypes={[{ code: "TYPE-A", name: "John Crane Type A" }]} />);

    expect(await screen.findByText("PHYSICAL SEAL WORKSPACE")).toBeTruthy();
    expect(screen.getAllByText(UNIT_ID).length).toBeGreaterThan(0);
    expect(screen.getByText(/Seal Type: TYPE-A \/ John Crane Type A/)).toBeTruthy();
    expect(screen.getByText(/Serial Number: N\/A/)).toBeTruthy();
    expect(screen.getByText(/Current Pump: 110-P-9A/)).toBeTruthy();
    expect(api.getSealUnits).toHaveBeenCalledOnce();
  });

  it("renders a clean zero-data state without fabricated seal units", () => {
    render(<PhysicalSealWorkspace units={[]} />);

    expect(screen.getByText("No physical seal units")).toBeTruthy();
  });

  it("hydrates lifecycle, inspection, repair, installation, warranty, and history read models", async () => {
    render(<PhysicalSealWorkspace units={units} />);

    expect(await screen.findByText(/2026-01-10 - INSTALL - Pump 110-P-9A/)).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Inspection" }));
    expect(screen.getByText(/2026-03-02 - FAILURE - WORN - Findings: 1/)).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Repair" }));
    expect(screen.getByText(/2026-03-03 - SHOP - SCRAPPED - Inspection insp-1/)).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Installation" }));
    expect(screen.getByText(/Report Date 2026-01-20 - Install Event N\/A/)).toBeTruthy();
    expect(screen.getByText(/Install event date is the authoritative fitment date/)).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Warranty" }));
    expect(screen.getByText(/18 calendar months/)).toBeTruthy();
    expect(screen.getByText("WITHIN_WARRANTY_WINDOW")).toBeTruthy();
    expect(screen.getByText("PENDING_EXAMINATION")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "History" }));
    expect(screen.getByText(/2026-04-01 - INSTALL - Pump 211-P-1A/)).toBeTruthy();
    expect(screen.getByText(/2026-03-02 - INSPECTION - Pump N\/A/)).toBeTruthy();
  });

  it("uses seal.lifecycle_write for write controls and still surfaces backend 403 detail", async () => {
    useOptionalAuth.mockReturnValue({ session: { permissions: ["seal.read"] } });
    render(<PhysicalSealWorkspace units={units} />);
    expect(await screen.findByText("Read-only: seal.lifecycle_write is required for append actions.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Lifecycle Action" }).disabled).toBe(true);
    cleanup();

    useOptionalAuth.mockReturnValue({ session: { permissions: ["seal.read", "seal.lifecycle_write"] } });
    api.createSealUnitLifecycleEvent.mockRejectedValueOnce(new Error("TAP_VIEWER is not authorized"));
    render(<PhysicalSealWorkspace units={units} />);
    fireEvent.click(await screen.findByRole("button", { name: "Lifecycle Action" }));
    fireEvent.change(screen.getByLabelText("Event Date"), { target: { value: "2026-04-01T08:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect((await screen.findByRole("alert")).textContent).toContain("TAP_VIEWER is not authorized");
  });

  it("posts lifecycle actions with backend-authoritative validation and requires install pump/date in the form", async () => {
    render(<PhysicalSealWorkspace units={[{ ...units[1], status: "SPARE" }]} />);
    fireEvent.click(await screen.findByRole("button", { name: "Lifecycle Action" }));

    expect(screen.getByLabelText("Action").value).toBe("INSTALL");
    expect(screen.getByLabelText("Event Date").required).toBe(true);
    fireEvent.change(screen.getByLabelText("Event Date"), { target: { value: "2026-04-01T08:00" } });
    fireEvent.change(screen.getByLabelText("Pump Tag"), { target: { value: "211-P-1A" } });
    fireEvent.change(screen.getByLabelText("Reason"), { target: { value: "commissioning" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => expect(api.createSealUnitLifecycleEvent).toHaveBeenCalledWith(OTHER_UNIT_ID, expect.objectContaining({ event_type: "INSTALL", pump_tag_number: "211-P-1A" })));
  });

  it("creates inspections with multiple findings and preserves numeric zero distinct from null", async () => {
    render(<PhysicalSealWorkspace units={units} />);
    fireEvent.click(await screen.findByRole("button", { name: "Add Inspection" }));
    fireEvent.change(screen.getByLabelText("Inspection Date"), { target: { value: "2026-03-02T09:00" } });
    fireEvent.change(screen.getByLabelText("Measured Value"), { target: { value: "0" } });
    fireEvent.change(screen.getByLabelText("Finding"), { target: { value: "face worn" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Finding Row" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => expect(api.createSealUnitInspection).toHaveBeenCalledWith(UNIT_ID, expect.objectContaining({ findings: expect.arrayContaining([expect.objectContaining({ component: "SEAL_FACE", measured_value: 0 })]) })));
  });

  it("creates repairs with linked inspection and does not infer SCRAPPED lifecycle state from repair result", async () => {
    render(<PhysicalSealWorkspace units={units} />);
    fireEvent.click(await screen.findByRole("button", { name: "Add Repair" }));
    fireEvent.change(screen.getByLabelText("Repair Date"), { target: { value: "2026-03-03T09:00" } });
    fireEvent.change(screen.getByLabelText("Linked Inspection"), { target: { value: "insp-1" } });
    fireEvent.change(screen.getByLabelText("Repair Result"), { target: { value: "SCRAPPED" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => expect(api.createSealUnitRepair).toHaveBeenCalledWith(UNIT_ID, expect.objectContaining({ inspection_id: "insp-1", repair_result: "SCRAPPED" })));
    expect(api.createSealUnitLifecycleEvent).not.toHaveBeenCalled();
  });

  it("links an existing installation report to an authoritative INSTALL event only", async () => {
    render(<PhysicalSealWorkspace units={units} />);
    fireEvent.click(await screen.findByRole("button", { name: "Link Installation Report" }));
    fireEvent.change(screen.getByLabelText("Installation Report"), { target: { value: "IR-1" } });
    fireEvent.change(screen.getByLabelText("INSTALL Event"), { target: { value: "evt-install" } });
    fireEvent.change(screen.getByLabelText("Pump Tag"), { target: { value: "110-P-9A" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => expect(api.linkInstallationReportToInstallEvent).toHaveBeenCalledWith("IR-1", expect.objectContaining({ seal_unit_id: UNIT_ID, installation_event_id: "evt-install" })));
  });

  it("creates warranty assessments as PENDING_EXAMINATION and records separate claim decisions", async () => {
    render(<PhysicalSealWorkspace units={units} />);
    fireEvent.click(await screen.findByRole("button", { name: "Assess Warranty" }));
    fireEvent.change(screen.getByLabelText("INSTALL Event"), { target: { value: "evt-install" } });
    fireEvent.click(screen.getByRole("button", { name: "Create PENDING_EXAMINATION" }));
    await waitFor(() => expect(api.createSealUnitWarrantyAssessment).toHaveBeenCalledWith(UNIT_ID, expect.objectContaining({ installation_event_id: "evt-install" })));

    fireEvent.click(await screen.findByRole("button", { name: "Assess Warranty" }));
    fireEvent.change(screen.getByLabelText("Assessment"), { target: { value: "wa-1" } });
    fireEvent.change(screen.getByLabelText("Decision"), { target: { value: "REJECTED" } });
    fireEvent.change(screen.getByLabelText("Decision Reason"), { target: { value: "outside scope" } });
    fireEvent.click(screen.getByRole("button", { name: "Record Decision" }));
    await waitFor(() => expect(api.decideSealWarrantyAssessment).toHaveBeenCalledWith("wa-1", expect.objectContaining({ decision: "REJECTED" })));
  });

  it("does not render edit delete upload stock reconciliation or CM failure linkage actions", async () => {
    render(<PhysicalSealWorkspace units={units} />);
    await screen.findByText("PHYSICAL SEAL WORKSPACE");
    const workspace = within(screen.getByLabelText("Physical Seal Workspace"));
    expect(workspace.queryByRole("button", { name: /delete/i })).toBeNull();
    expect(workspace.queryByRole("button", { name: /edit/i })).toBeNull();
    expect(workspace.queryByText(/upload/i)).toBeNull();
    expect(workspace.queryByText(/stock reconciliation/i)).toBeNull();
    expect(workspace.queryByText(/failure linkage/i)).toBeNull();
  });
});