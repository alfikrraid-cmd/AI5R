import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PumpXlsxImportPanel from "./PumpXlsxImportPanel";
import { dryRunPumpXlsx, executeImportSession } from "../../../api/ai5rClient";

// MWO-LTSA-DATA-IMPORT-UI-001B/-001C -- mirrors ImportWorkspace.test.jsx's
// own vi.mock("../../../api/ai5rClient") convention: both real API
// contracts (multipart dry-run upload, POST .../execute) were already
// proven live via TestClient(app) in CORE-SERVICES/BACKEND-API/TESTS/
// test_import_router.py; this file only proves the panel renders whatever
// the API returns, correctly, and sends exactly session_id to Approve --
// never a re-upload, never re-sent parsed data.
vi.mock("../../../api/ai5rClient", () => ({
  dryRunPumpXlsx: vi.fn(),
  executeImportSession: vi.fn(),
}));

function xlsxFile(name = "master.xlsx") {
  return new File(["fake-xlsx-bytes"], name, {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

const REAL_FILE_REPORT = {
  session_id: "DRYRUN-1",
  source: "/tmp/master.xlsx",
  sheet: "Master Pump",
  source_count: 244,
  normalized_count: 244,
  valid_count: 239,
  warning_count: 0,
  rejected_count: 5,
  duplicate_count: 0,
  new_count: 244,
  update_count: 0,
  mapped_columns: { "Tag Number": "tag_number", Area: "area", "Pump Type": "pump_type" },
  unmapped_columns: ["Pump ID", "Service"],
  row_issues: [
    { severity: "ERROR", code: "MISSING_REQUIRED_FIELD", entity_id: "211-P-13AR", field: "area", message: "pump record is missing required field 'area'" },
  ],
  preview_rows: [{ tag_number: "101-P-10A", area: "HSC", pump_type: "OH", api_plan: "11/61" }],
  approval_ready: false,
};

const VALID_REPORT = {
  ...REAL_FILE_REPORT,
  session_id: "DRYRUN-VALID-1",
  rejected_count: 0,
  valid_count: 244,
  row_issues: [],
  approval_ready: true,
};

const EXECUTION_RESULT_COMMITTED = {
  session_id: "DRYRUN-VALID-1",
  status: "COMMITTED",
  reason: null,
  statistics: {
    pump: { inserted: 244, updated: 0, skipped: 0, failed: 0 },
    seal: { inserted: 0, updated: 0, skipped: 0, failed: 0 },
    installation: { inserted: 0, updated: 0, skipped: 0, failed: 0 },
    document: { inserted: 0, updated: 0, skipped: 0, failed: 0 },
  },
  execution_log: [],
};

beforeEach(() => {
  dryRunPumpXlsx.mockReset();
  executeImportSession.mockReset();
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

async function analyzeWith(data) {
  dryRunPumpXlsx.mockResolvedValue({ success: true, data });
  render(<PumpXlsxImportPanel />);
  fireEvent.change(screen.getByLabelText("Upload Pump Master XLSX"), { target: { files: [xlsxFile()] } });
  fireEvent.click(screen.getByText("Analyze / Dry Run"));
  await waitFor(() => expect(screen.getByTestId("pump-xlsx-report")).toBeTruthy());
}

describe("PumpXlsxImportPanel", () => {
  it("accepts a dropped .xlsx file and shows its filename", () => {
    render(<PumpXlsxImportPanel />);
    const dropzone = screen.getByTestId("pump-xlsx-dropzone");

    fireEvent.drop(dropzone, { dataTransfer: { files: [xlsxFile("master.xlsx")] } });

    expect(screen.getByTestId("pump-xlsx-filename").textContent).toBe("master.xlsx");
  });

  it("accepts a file chosen via the file picker input", () => {
    render(<PumpXlsxImportPanel />);
    const input = screen.getByLabelText("Upload Pump Master XLSX");

    fireEvent.change(input, { target: { files: [xlsxFile("picked.xlsx")] } });

    expect(screen.getByTestId("pump-xlsx-filename").textContent).toBe("picked.xlsx");
  });

  it("rejects an invalid extension without calling the API", () => {
    render(<PumpXlsxImportPanel />);
    const dropzone = screen.getByTestId("pump-xlsx-dropzone");

    fireEvent.drop(dropzone, { dataTransfer: { files: [new File(["x"], "notes.txt", { type: "text/plain" })] } });

    expect(screen.getByTestId("pump-xlsx-reject-message").textContent).toMatch(/not a \.xlsx\/\.xls file/);
    expect(screen.queryByTestId("pump-xlsx-filename")).toBeNull();
    expect(dryRunPumpXlsx).not.toHaveBeenCalled();
  });

  it("Analyze / Dry Run stays disabled until a valid file is selected", () => {
    render(<PumpXlsxImportPanel />);
    expect(screen.getByText("Analyze / Dry Run").closest("button").disabled).toBe(true);
  });

  it("renders the real acceptance-file counts, mapping, row issues, and preview after Analyze", async () => {
    dryRunPumpXlsx.mockResolvedValue({ success: true, data: REAL_FILE_REPORT });
    render(<PumpXlsxImportPanel />);
    fireEvent.change(screen.getByLabelText("Upload Pump Master XLSX"), { target: { files: [xlsxFile()] } });

    fireEvent.click(screen.getByText("Analyze / Dry Run"));

    await waitFor(() => expect(screen.getByTestId("pump-xlsx-report")).toBeTruthy());
    const report = screen.getByTestId("pump-xlsx-report");
    expect(report.textContent).toContain("Master Pump");
    expect(report.textContent).toContain("source_count: 244");
    expect(report.textContent).toContain("normalized_count: 244");
    expect(report.textContent).toContain("Valid: 239");
    expect(report.textContent).toContain("Warning: 0");
    expect(report.textContent).toContain("Rejected: 5");
    expect(report.textContent).toContain("INSERT: 244");
    expect(report.textContent).toContain("UPDATE: 0");
    expect(report.textContent).toContain("SKIP: 0");
    expect(screen.getByTestId("pump-xlsx-approval-ready").textContent).toContain("false");
    expect(report.textContent).toContain("211-P-13AR");
    expect(report.textContent).toContain("missing required field 'area'");
    expect(report.textContent).toContain("Tag Number -> tag_number");
    expect(report.textContent).toContain("Pump ID, Service");
    expect(report.textContent).toContain("101-P-10A");
  });

  it("keeps Approve Import disabled while approval_ready is false, with the rejection reason shown", async () => {
    await analyzeWith(REAL_FILE_REPORT);

    expect(screen.getByText("Approve Import").closest("button").disabled).toBe(true);
    expect(screen.getByTestId("pump-xlsx-approve-note").textContent).toMatch(/5 rejected row/);
    expect(executeImportSession).not.toHaveBeenCalled();
  });

  it("enables Approve Import when approval_ready is true", async () => {
    await analyzeWith(VALID_REPORT);

    expect(screen.getByText("Approve Import").closest("button").disabled).toBe(false);
    expect(screen.queryByTestId("pump-xlsx-approve-note")).toBeNull();
  });

  it("asks for confirmation before calling execute, and does nothing if the user cancels", async () => {
    window.confirm.mockReturnValue(false);
    await analyzeWith(VALID_REPORT);

    fireEvent.click(screen.getByText("Approve Import"));

    expect(window.confirm).toHaveBeenCalled();
    expect(executeImportSession).not.toHaveBeenCalled();
  });

  it("Approve sends only the session_id, never a re-upload or re-sent data", async () => {
    executeImportSession.mockResolvedValue({ success: true, data: EXECUTION_RESULT_COMMITTED });
    await analyzeWith(VALID_REPORT);

    fireEvent.click(screen.getByText("Approve Import"));

    await waitFor(() => expect(executeImportSession).toHaveBeenCalledWith("DRYRUN-VALID-1"));
    expect(executeImportSession).toHaveBeenCalledTimes(1);
  });

  it("renders the execution result (INSERT/UPDATE/SKIP) after a successful Approve and hides the button", async () => {
    executeImportSession.mockResolvedValue({ success: true, data: EXECUTION_RESULT_COMMITTED });
    await analyzeWith(VALID_REPORT);

    fireEvent.click(screen.getByText("Approve Import"));

    await waitFor(() => expect(screen.getByTestId("pump-xlsx-execution-result")).toBeTruthy());
    const result = screen.getByTestId("pump-xlsx-execution-result");
    expect(result.textContent).toContain("COMMITTED");
    expect(result.textContent).toContain("DRYRUN-VALID-1");
    expect(result.textContent).toContain("Inserted: 244");
    expect(screen.queryByText("Approve Import")).toBeNull();
  });

  it("shows a safe error when Approve reports success:false (e.g. rejected/already-executed session)", async () => {
    executeImportSession.mockResolvedValue({
      success: false,
      message: "Import session 'DRYRUN-VALID-1' has already been executed (status=IMPORTED)",
      data: null,
    });
    await analyzeWith(VALID_REPORT);

    fireEvent.click(screen.getByText("Approve Import"));

    await waitFor(() => expect(screen.getByTestId("pump-xlsx-approve-error")).toBeTruthy());
    expect(screen.getByTestId("pump-xlsx-approve-error").textContent).toContain("already been executed");
    expect(screen.queryByTestId("pump-xlsx-execution-result")).toBeNull();
  });

  it("shows a real API-level error state on Approve without crashing", async () => {
    executeImportSession.mockRejectedValue(new Error("Import API /api/ltsa/import/execute unavailable"));
    await analyzeWith(VALID_REPORT);

    fireEvent.click(screen.getByText("Approve Import"));

    await waitFor(() => expect(screen.getByTestId("pump-xlsx-approve-error")).toBeTruthy());
    expect(screen.getByTestId("pump-xlsx-approve-error").textContent).toContain("unavailable");
  });

  it("shows the backend's own message when the dry-run reports success:false", async () => {
    dryRunPumpXlsx.mockResolvedValue({ success: false, message: "Unsupported file type '.csv'", data: null });
    render(<PumpXlsxImportPanel />);
    fireEvent.change(screen.getByLabelText("Upload Pump Master XLSX"), { target: { files: [xlsxFile()] } });

    fireEvent.click(screen.getByText("Analyze / Dry Run"));

    await waitFor(() => expect(screen.getByTestId("pump-xlsx-error")).toBeTruthy());
    expect(screen.getByTestId("pump-xlsx-error").textContent).toContain("Unsupported file type");
    expect(screen.queryByTestId("pump-xlsx-report")).toBeNull();
  });

  it("shows a real API-level error state without crashing", async () => {
    dryRunPumpXlsx.mockRejectedValue(new Error("Pump XLSX dry-run API unavailable"));
    render(<PumpXlsxImportPanel />);
    fireEvent.change(screen.getByLabelText("Upload Pump Master XLSX"), { target: { files: [xlsxFile()] } });

    fireEvent.click(screen.getByText("Analyze / Dry Run"));

    await waitFor(() => expect(screen.getByTestId("pump-xlsx-error")).toBeTruthy());
    expect(screen.getByTestId("pump-xlsx-error").textContent).toContain("API unavailable");
  });
});
