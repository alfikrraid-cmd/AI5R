import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PMExcelImportPanel from "./PMExcelImportPanel";
import { getPumps, parsePMScheduleExcel, downloadPMScheduleImportTemplate } from "../../../api/ai5rClient";

// AI5R-PHASE4E4 -- covers the DOM-level subset of Section Q's import
// requirements: the mandatory Excel -> parse -> preview -> "Review in
// Bulk Editor" handoff (never a direct create), rejecting non-.xlsx
// files, showing the File/Rows/Mapped/Warnings/Errors preview, blocking
// on a structural error (missing required column), and readable parse
// errors. Field-level mapping/validation rules (header aliases, pump
// resolution, frequency/date/activity parsing) are covered exhaustively
// by pmExcelImport.test.js's pure-function tests -- this file proves the
// panel wires those functions up correctly.
vi.mock("../../../api/ai5rClient", () => ({
  getPumps: vi.fn(),
  parsePMScheduleExcel: vi.fn(),
  downloadPMScheduleImportTemplate: vi.fn(),
}));

const PUMPS = [{ tag_number: "211-P-1A", name: "Boiler Feedwater Pump 1A" }];

function makeXlsxFile(name = "schedules.xlsx") {
  return new File(["dummy"], name, { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

function uploadFile(file) {
  fireEvent.change(screen.getByLabelText("Upload PM Schedule Excel file"), { target: { files: [file] } });
}

describe("PMExcelImportPanel -- file acceptance", () => {
  it("rejects a non-.xlsx file with a readable message", () => {
    render(<PMExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);

    uploadFile(new File(["x"], "schedules.csv", { type: "text/csv" }));

    expect(screen.getByText(/is not a \.xlsx file/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Parse File" })).toBeDisabled();
  });

  it("accepts a .xlsx file and enables Parse File", () => {
    render(<PMExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);

    uploadFile(makeXlsxFile());

    expect(screen.getByText("schedules.xlsx")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Parse File" })).not.toBeDisabled();
  });
});

describe("PMExcelImportPanel -- parse preview", () => {
  it("shows File/Rows detected/Mapped/Warnings/Errors, and never creates anything directly", async () => {
    getPumps.mockResolvedValue(PUMPS);
    parsePMScheduleExcel.mockResolvedValue({
      data: {
        headers: ["Pump Tag", "Frequency", "Start Date"],
        rows: [["211-P-1A", "MONTHLY", "2026-10-01"]],
      },
    });
    render(<PMExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);
    uploadFile(makeXlsxFile());

    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));

    expect(await screen.findByTestId("pm-excel-import-preview")).toBeTruthy();
    expect(screen.getByText("Rows detected: 1")).toBeTruthy();
    expect(screen.getByText("Mapped: 3 column(s)")).toBeTruthy();
    expect(screen.getByText("Warnings: 0")).toBeTruthy();
    expect(screen.getByText("Errors: 0")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Review in Bulk Editor" })).not.toBeDisabled();
  });

  it("hands parsed rows to onReviewInBulkEditor, in the same row model the Bulk Editor uses", async () => {
    getPumps.mockResolvedValue(PUMPS);
    parsePMScheduleExcel.mockResolvedValue({
      data: { headers: ["Pump Tag", "Frequency", "Start Date"], rows: [["211-P-1A", "MONTHLY", "2026-10-01"]] },
    });
    const onReviewInBulkEditor = vi.fn();
    render(<PMExcelImportPanel onClose={() => {}} onReviewInBulkEditor={onReviewInBulkEditor} />);
    uploadFile(makeXlsxFile());
    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));
    await screen.findByTestId("pm-excel-import-preview");

    fireEvent.click(screen.getByRole("button", { name: "Review in Bulk Editor" }));

    expect(onReviewInBulkEditor).toHaveBeenCalledOnce();
    const rows = onReviewInBulkEditor.mock.calls[0][0];
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({ pumpTag: "211-P-1A", frequency: "MONTHLY", startDate: "2026-10-01", source: "EXCEL_IMPORT", sourceRow: 2 });
  });

  it("shows a warning for an unknown column without blocking the import", async () => {
    getPumps.mockResolvedValue(PUMPS);
    parsePMScheduleExcel.mockResolvedValue({
      data: { headers: ["Pump Tag", "Frequency", "Start Date", "Foo"], rows: [["211-P-1A", "MONTHLY", "2026-10-01", "x"]] },
    });
    render(<PMExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);
    uploadFile(makeXlsxFile());
    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));

    await screen.findByTestId("pm-excel-import-preview");
    expect(screen.getByText("Warnings: 1")).toBeTruthy();
    expect(screen.getByText(/Foo/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Review in Bulk Editor" })).not.toBeDisabled();
  });

  it("blocks entirely on a structural error (missing required column) -- no Review button, do not continue", async () => {
    getPumps.mockResolvedValue(PUMPS);
    parsePMScheduleExcel.mockResolvedValue({
      data: { headers: ["Pump Tag", "Frequency"], rows: [["211-P-1A", "MONTHLY"]] },
    });
    render(<PMExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);
    uploadFile(makeXlsxFile());
    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));

    expect(await screen.findByText(/Missing required column/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Review in Bulk Editor" })).toBeNull();
  });

  it("retains rows with row-level errors instead of discarding them, and does not block Review", async () => {
    getPumps.mockResolvedValue(PUMPS);
    parsePMScheduleExcel.mockResolvedValue({
      data: {
        headers: ["Pump Tag", "Frequency", "Start Date"],
        rows: [
          ["211-P-1A", "MONTHLY", "2026-10-01"],
          ["999-P-XYZ", "MONTHLY", "2026-10-01"],
        ],
      },
    });
    const onReviewInBulkEditor = vi.fn();
    render(<PMExcelImportPanel onClose={() => {}} onReviewInBulkEditor={onReviewInBulkEditor} />);
    uploadFile(makeXlsxFile());
    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));

    await screen.findByTestId("pm-excel-import-preview");
    expect(screen.getByText("Rows detected: 2")).toBeTruthy();
    expect(screen.getByText("Errors: 1")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Review in Bulk Editor" }));
    expect(onReviewInBulkEditor.mock.calls[0][0]).toHaveLength(2); // both rows proceed, none silently dropped
  });

  it("shows a readable parse error, never [object Object]", async () => {
    getPumps.mockResolvedValue(PUMPS);
    const error = new Error("The file could not be read as a valid .xlsx workbook.");
    parsePMScheduleExcel.mockRejectedValue(error);
    render(<PMExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);
    uploadFile(makeXlsxFile());

    fireEvent.click(screen.getByRole("button", { name: "Parse File" }));

    expect(await screen.findByText("The file could not be read as a valid .xlsx workbook.")).toBeTruthy();
    expect(screen.queryByText(/object Object/i)).toBeNull();
  });
});

describe("PMExcelImportPanel -- template download", () => {
  it("downloads the template via the API, never generating it in the browser", async () => {
    const blob = new Blob(["x"], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
    downloadPMScheduleImportTemplate.mockResolvedValue(blob);
    render(<PMExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Download Excel Template" }));

    await waitFor(() => expect(downloadPMScheduleImportTemplate).toHaveBeenCalledOnce());
  });

  it("shows a readable error if the template download fails", async () => {
    downloadPMScheduleImportTemplate.mockRejectedValue(new Error("PM Schedule import template API unavailable"));
    render(<PMExcelImportPanel onClose={() => {}} onReviewInBulkEditor={() => {}} />);

    fireEvent.click(screen.getByRole("button", { name: "Download Excel Template" }));

    expect(await screen.findByText("PM Schedule import template API unavailable")).toBeTruthy();
  });
});
