import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PumpXlsxImportPanel from "./PumpXlsxImportPanel";
import { dryRunPumpXlsx } from "../../../api/ai5rClient";

// MWO-LTSA-DATA-IMPORT-UI-001B -- mirrors ImportWorkspace.test.jsx's own
// vi.mock("../../../api/ai5rClient") convention: the real multipart upload
// contract was already proven live via TestClient(app) in
// CORE-SERVICES/BACKEND-API/TESTS/test_import_router.py; this file only
// proves the panel renders whatever the API returns, correctly.
vi.mock("../../../api/ai5rClient", () => ({
  dryRunPumpXlsx: vi.fn(),
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

beforeEach(() => {
  dryRunPumpXlsx.mockReset();
});

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

  it("keeps Approve Import disabled even when approval_ready is true", async () => {
    dryRunPumpXlsx.mockResolvedValue({
      success: true,
      data: { ...REAL_FILE_REPORT, rejected_count: 0, valid_count: 244, row_issues: [], approval_ready: true },
    });
    render(<PumpXlsxImportPanel />);
    fireEvent.change(screen.getByLabelText("Upload Pump Master XLSX"), { target: { files: [xlsxFile()] } });
    fireEvent.click(screen.getByText("Analyze / Dry Run"));

    await waitFor(() => expect(screen.getByTestId("pump-xlsx-approval-ready").textContent).toContain("true"));

    expect(screen.getByText("Approve Import").closest("button").disabled).toBe(true);
    expect(screen.getByTestId("pump-xlsx-approve-note").textContent).toMatch(/001C/);
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
