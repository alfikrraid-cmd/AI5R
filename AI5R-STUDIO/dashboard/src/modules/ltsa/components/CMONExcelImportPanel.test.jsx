import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CMONExcelImportPanel from "./CMONExcelImportPanel";
import { getPumps, parseConditionMonitoringExcel, downloadConditionMonitoringImportTemplate } from "../../../api/ai5rClient";

// MWO-LTSA-CMON-EXCEL-IMPORT-001 -- covers the DOM-level subset of
// requirements: the mandatory Excel -> parse -> preview -> "Review in
// Bulk Editor" handoff (never a direct create), rejecting non-.xlsx
// files, showing the File/Rows/Mapped/Warnings/Errors preview, blocking
// on a structural error (missing Pump Tag column), and readable parse
// errors. Field-level mapping/validation rules are covered exhaustively
// by conditionMonitoringExcelImport.test.js's pure-function tests --
// this file proves the panel wires those functions up correctly.
vi.mock("../../../api/ai5rClient", () => ({
  getPumps: vi.fn(),
  parseConditionMonitoringExcel: vi.fn(),
  downloadConditionMonitoringImportTemplate: vi.fn(),
}));

const PUMPS = [{ tag_number: "211-P-1A", name: "Boiler Feedwater Pump 1A" }];

function makeXlsxFile(name = "readings.xlsx") {
  return new File(["dummy"], name, { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

function uploadFile(file) {
  fireEvent.change(screen.getByLabelText("Upload Condition Monitoring Excel file"), { target: { files: [file] } });
}

describe("CMONExcelImportPanel -- file acceptance", () => {
  it("rejects a non-.xlsx (.csv) file with a readable message", () => {
    render(<CMONExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);

    uploadFile(new File(["x"], "readings.csv", { type: "text/csv" }));

    expect(screen.getByText(/is not a \.xlsx file/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Parse File" })).toBeDisabled();
  });

  it("rejects a legacy .xls file", () => {
    render(<CMONExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);

    uploadFile(new File(["x"], "readings.xls", { type: "application/vnd.ms-excel" }));

    expect(screen.getByText(/is not a \.xlsx file/)).toBeTruthy();
  });

  it("accepts a .xlsx file and enables Parse File", () => {
    render(<CMONExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);

    uploadFile(makeXlsxFile());

    expect(screen.getByText("readings.xlsx")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Parse File" })).not.toBeDisabled();
  });
});

describe("CMONExcelImportPanel -- parse preview", () => {
  it("shows File/Rows detected/Mapped/Warnings/Errors, and never creates anything directly", async () => {
    getPumps.mockResolvedValue(PUMPS);
    parseConditionMonitoringExcel.mockResolvedValue({
      data: {
        headers: ["Pump Tag *", "Reading Date *", "Mechanical Seal Temp DE"],
        rows: [["211-P-1A", "2026-09-06", "75.2"]],
      },
    });
    render(<CMONExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);
    uploadFile(makeXlsxFile());

    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));

    expect(await screen.findByTestId("cmon-excel-import-preview")).toBeTruthy();
    expect(screen.getByText("Rows detected: 1")).toBeTruthy();
    expect(screen.getByText("Mapped: 3 column(s)")).toBeTruthy();
    expect(screen.getByText("Warnings: 0")).toBeTruthy();
    expect(screen.getByText("Errors: 0")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Review in Bulk Editor" })).not.toBeDisabled();
  });

  it("hands parsed rows to onReviewInBulkEditor, in the same row model the Bulk Editor uses", async () => {
    getPumps.mockResolvedValue(PUMPS);
    parseConditionMonitoringExcel.mockResolvedValue({
      data: {
        headers: ["Pump Tag *", "Reading Date *", "Mechanical Seal Temp DE"],
        rows: [["211-P-1A", "2026-09-06", "75.2"]],
      },
    });
    const onReviewInBulkEditor = vi.fn();
    render(<CMONExcelImportPanel onClose={() => {}} onReviewInBulkEditor={onReviewInBulkEditor} />);
    uploadFile(makeXlsxFile());
    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));
    await screen.findByTestId("cmon-excel-import-preview");

    fireEvent.click(screen.getByRole("button", { name: "Review in Bulk Editor" }));

    expect(onReviewInBulkEditor).toHaveBeenCalledOnce();
    const rows = onReviewInBulkEditor.mock.calls[0][0];
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({ pumpTag: "211-P-1A", readingDate: "2026-09-06", source: "EXCEL_IMPORT", sourceRow: 2 });
    expect(rows[0].measurements.mechsealTempDe).toBe("75.2");
  });

  it("shows a warning for an unknown column without blocking the import", async () => {
    getPumps.mockResolvedValue(PUMPS);
    parseConditionMonitoringExcel.mockResolvedValue({
      data: { headers: ["Pump Tag *", "Reading Date *", "Foo"], rows: [["211-P-1A", "2026-09-06", "x"]] },
    });
    render(<CMONExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);
    uploadFile(makeXlsxFile());
    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));

    await screen.findByTestId("cmon-excel-import-preview");
    expect(screen.getByText("Warnings: 1")).toBeTruthy();
    expect(screen.getByText(/Foo/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Review in Bulk Editor" })).not.toBeDisabled();
  });

  it("blocks entirely on a structural error (missing Pump Tag column) -- no Review button, do not continue", async () => {
    getPumps.mockResolvedValue(PUMPS);
    parseConditionMonitoringExcel.mockResolvedValue({
      data: { headers: ["Reading Date *"], rows: [["2026-09-06"]] },
    });
    render(<CMONExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);
    uploadFile(makeXlsxFile());
    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));

    expect(await screen.findByText(/Missing required column/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Review in Bulk Editor" })).toBeNull();
  });

  it("retains rows with row-level errors (unknown pump) instead of discarding them, and does not block Review", async () => {
    getPumps.mockResolvedValue(PUMPS);
    parseConditionMonitoringExcel.mockResolvedValue({
      data: {
        headers: ["Pump Tag *", "Reading Date *"],
        rows: [
          ["211-P-1A", "2026-09-06"],
          ["999-P-XYZ", "2026-09-06"],
        ],
      },
    });
    const onReviewInBulkEditor = vi.fn();
    render(<CMONExcelImportPanel onClose={() => {}} onReviewInBulkEditor={onReviewInBulkEditor} />);
    uploadFile(makeXlsxFile());
    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));

    await screen.findByTestId("cmon-excel-import-preview");
    expect(screen.getByText("Rows detected: 2")).toBeTruthy();
    expect(screen.getByText("Errors: 1")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Review in Bulk Editor" }));
    expect(onReviewInBulkEditor.mock.calls[0][0]).toHaveLength(2); // both rows proceed, none silently dropped
  });

  it("shows a readable parse error, never [object Object]", async () => {
    getPumps.mockResolvedValue(PUMPS);
    const error = new Error("The file could not be read as a valid .xlsx workbook.");
    parseConditionMonitoringExcel.mockRejectedValue(error);
    render(<CMONExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);
    uploadFile(makeXlsxFile());

    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));

    expect(await screen.findByText("The file could not be read as a valid .xlsx workbook.")).toBeTruthy();
    expect(screen.queryByText(/object Object/i)).toBeNull();
  });
});

describe("CMONExcelImportPanel -- template download", () => {
  it("downloads the template via the API, never generating it in the browser", async () => {
    const blob = new Blob(["x"], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
    downloadConditionMonitoringImportTemplate.mockResolvedValue(blob);
    render(<CMONExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Download Excel Template" }));

    await waitFor(() => expect(downloadConditionMonitoringImportTemplate).toHaveBeenCalledOnce());
  });

  it("shows a readable error if the template download fails", async () => {
    downloadConditionMonitoringImportTemplate.mockRejectedValue(new Error("Condition Monitoring import template API unavailable"));
    render(<CMONExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Download Excel Template" }));

    expect(await screen.findByText("Condition Monitoring import template API unavailable")).toBeTruthy();
  });
});
