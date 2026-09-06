import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import BulkPMScheduleEditor from "./BulkPMScheduleEditor";
import { getPumps, bulkCreatePMSchedules } from "../../../api/ai5rClient";

// AI5R-PHASE4E3 -- covers the DOM-level subset of Section P's 33 focused
// requirements (empty table, add/remove/duplicate row, canonical pump
// selection, multi-pump row generation, selection controls, apply-to-
// selected, activity taxonomy shape reachable through the UI, the
// Validate -> Confirm gate, edit-invalidates-validation, and readable
// submit errors). Payload-shape/validation-logic requirements (exact
// planned payload, no done, no legacy code, duplicate detection) are
// covered more directly and exhaustively by pmBulkSchedule.test.js's
// pure-function tests; this file proves the UI wires those functions up
// correctly rather than re-deriving every case at the DOM level.
vi.mock("../../../api/ai5rClient", () => ({
  getPumps: vi.fn(),
  bulkCreatePMSchedules: vi.fn(),
}));

const PUMPS = [
  { tag_number: "211-P-1A", name: "Boiler Feedwater Pump 1A" },
  { tag_number: "211-P-1B", name: "Boiler Feedwater Pump 1B" },
  { tag_number: "533-P-1", name: "Standby Transfer Pump" },
];

function loadPumps(pumps = PUMPS) {
  getPumps.mockResolvedValue(pumps);
}

async function renderEditor(props = {}) {
  const onClose = props.onClose || vi.fn();
  const onCreated = props.onCreated || vi.fn();
  const utils = render(
    <BulkPMScheduleEditor onClose={onClose} onCreated={onCreated} existingSchedules={props.existingSchedules || []} />
  );
  await screen.findByTestId("bulk-pm-schedule-editor");
  return { ...utils, onClose, onCreated };
}

describe("BulkPMScheduleEditor -- empty table", () => {
  it("starts empty, with Validate and Confirm both disabled", async () => {
    loadPumps();
    await renderEditor();

    expect(screen.getByText(/No rows yet/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Validate" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Confirm Create" })).toBeDisabled();
  });
});

describe("BulkPMScheduleEditor -- add/remove/duplicate row", () => {
  it("adds a row with + Add Row and removes it with Remove", async () => {
    loadPumps();
    await renderEditor();

    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));
    expect(screen.getAllByRole("button", { name: "Remove" })).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    expect(screen.queryByRole("button", { name: "Remove" })).toBeNull();
    expect(screen.getByText(/No rows yet/)).toBeTruthy();
  });

  it("duplicates a row's values into a new row", async () => {
    loadPumps();
    await renderEditor();
    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));

    const firstRow = screen.getAllByRole("row")[1]; // [0] is the header row
    fireEvent.change(within(firstRow).getByLabelText("Pump"), { target: { value: "211-P-1A" } });
    fireEvent.click(screen.getByRole("button", { name: "Duplicate" }));

    const pumpSelects = screen.getAllByLabelText("Pump");
    expect(pumpSelects).toHaveLength(2);
    expect(pumpSelects[0].value).toBe("211-P-1A");
    expect(pumpSelects[1].value).toBe("211-P-1A");
  });
});

describe("BulkPMScheduleEditor -- canonical pump selection", () => {
  it("offers only canonical pumps in each row's selector, never free text", async () => {
    loadPumps();
    await renderEditor();
    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));

    const select = screen.getByLabelText("Pump");
    expect(select.tagName).toBe("SELECT");
    const optionValues = Array.from(select.querySelectorAll("option")).map((o) => o.value);
    expect(optionValues).toEqual(["", "211-P-1A", "211-P-1B", "533-P-1"]);
  });
});

describe("BulkPMScheduleEditor -- multi-pump row generation", () => {
  it("generates one row per selected pump via + Add Pumps...", async () => {
    loadPumps();
    await renderEditor();

    fireEvent.click(screen.getByRole("button", { name: "+ Add Pumps..." }));
    fireEvent.click(screen.getByText("211-P-1A — Boiler Feedwater Pump 1A"));
    fireEvent.click(screen.getByText("533-P-1 — Standby Transfer Pump"));
    fireEvent.click(screen.getByRole("button", { name: /Add 2 Rows/ }));

    const pumpSelects = screen.getAllByLabelText("Pump");
    expect(pumpSelects.map((s) => s.value).sort()).toEqual(["211-P-1A", "533-P-1"]);
  });
});

describe("BulkPMScheduleEditor -- selection controls", () => {
  it("selects all and clears selection", async () => {
    loadPumps();
    await renderEditor();
    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));
    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));

    fireEvent.click(screen.getByRole("button", { name: "Select All" }));
    for (const checkbox of screen.getAllByRole("checkbox", { name: /Select row/ })) {
      expect(checkbox.checked).toBe(true);
    }

    fireEvent.click(screen.getByRole("button", { name: "Clear Selection" }));
    for (const checkbox of screen.getAllByRole("checkbox", { name: /Select row/ })) {
      expect(checkbox.checked).toBe(false);
    }
  });
});

describe("BulkPMScheduleEditor -- apply to selected", () => {
  async function twoRowsOneSelected() {
    loadPumps();
    const utils = await renderEditor();
    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));
    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));
    const checkboxes = screen.getAllByRole("checkbox", { name: /Select row/ });
    fireEvent.click(checkboxes[0]); // select only the first row
    return utils;
  }

  it("applies Frequency only to selected rows, leaving the unselected row unchanged", async () => {
    await twoRowsOneSelected();
    fireEvent.change(screen.getByLabelText("Apply Frequency"), { target: { value: "RUNTIME_BASED" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply to Selected" }));

    const frequencySelects = screen.getAllByLabelText(/^Frequency for row/);
    expect(frequencySelects[0].value).toBe("RUNTIME_BASED");
    expect(frequencySelects[1].value).toBe("MONTHLY"); // unselected row untouched
  });

  it("applies Start Date only to selected rows", async () => {
    await twoRowsOneSelected();
    fireEvent.change(screen.getByLabelText("Apply Start Date"), { target: { value: "2026-12-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply to Selected" }));

    const dateInputs = screen.getAllByLabelText(/^Start Date for row/);
    expect(dateInputs[0].value).toBe("2026-12-01");
    expect(dateInputs[1].value).not.toBe("2026-12-01");
  });

  it("applies Assigned Technician only to selected rows", async () => {
    await twoRowsOneSelected();
    fireEvent.change(screen.getByLabelText("Apply Assigned Technician"), { target: { value: "Bagus Setiawan" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply to Selected" }));

    const techInputs = screen.getAllByLabelText(/^Assigned Technician for row/);
    expect(techInputs[0].value).toBe("Bagus Setiawan");
    expect(techInputs[1].value).toBe("");
  });

  it("applies Duration only to selected rows, and a blank apply field leaves it unchanged", async () => {
    await twoRowsOneSelected();
    fireEvent.change(screen.getByLabelText("Apply Duration"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply to Selected" }));

    const durationInputs = screen.getAllByLabelText(/^Duration for row/);
    expect(durationInputs[0].value).toBe("4");
    expect(durationInputs[1].value).toBe("");
  });

  it("applies Activities to Selected only after the explicit Apply action, never automatically", async () => {
    await twoRowsOneSelected();
    fireEvent.click(screen.getByRole("button", { name: "Apply Activities to Selected..." }));
    fireEvent.click(screen.getByLabelText("Reservoir"));
    // Not yet applied -- closing without clicking Apply must not touch any row.
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getAllByText("0 selected")).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "Apply Activities to Selected..." }));
    fireEvent.click(screen.getByLabelText("Reservoir"));
    fireEvent.click(screen.getByRole("button", { name: "Apply Activities" }));

    const counts = screen.getAllByText(/selected$/).map((el) => el.textContent);
    expect(counts).toEqual(["1 selected", "0 selected"]); // only the selected row changed
  });
});

describe("BulkPMScheduleEditor -- planned activities taxonomy reachable through the row editor", () => {
  it("opens with every activity unchecked, General/DE/NDE independent, Reservoir General-only", async () => {
    loadPumps();
    await renderEditor();
    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByLabelText("Reservoir")).toBeTruthy();
    expect(screen.queryByLabelText("Reservoir DE Side")).toBeNull();

    for (const checkbox of screen.getAllByRole("checkbox")) {
      if (checkbox.getAttribute("aria-label")) {
        expect(checkbox.checked).toBe(false);
      }
    }

    fireEvent.click(screen.getByLabelText("Flushing Line DE Side"));
    expect(screen.getByLabelText("Flushing Line DE Side").checked).toBe(true);
    expect(screen.getByLabelText("Flushing Line NDE Side").checked).toBe(false);

    expect(screen.getByLabelText("Cooler")).toBeTruthy();
    expect(screen.getByLabelText("Cooling Water Cooler")).toBeTruthy();
    expect(screen.queryByText(/WCH/)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByText("1 selected")).toBeTruthy();
  });
});

describe("BulkPMScheduleEditor -- Validate / Confirm gate", () => {
  it("blocks Confirm when Validate finds an error, and shows the summary", async () => {
    loadPumps();
    await renderEditor();
    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" })); // pump left blank -> ERROR

    fireEvent.click(screen.getByRole("button", { name: "Validate" }));

    expect(await screen.findByTestId("bulk-validation-summary")).toHaveTextContent("Errors: 1");
    expect(screen.getByRole("button", { name: "Confirm Create" })).toBeDisabled();
  });

  it("does not block Confirm when Validate finds only a warning", async () => {
    loadPumps();
    const existingSchedules = [{ equipmentTag: "211-P-1A", frequency: "MONTHLY", status: "ACTIVE" }];
    await renderEditor({ existingSchedules });
    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));
    fireEvent.change(screen.getByLabelText("Pump"), { target: { value: "211-P-1A" } });

    fireEvent.click(screen.getByRole("button", { name: "Validate" }));

    expect(await screen.findByTestId("bulk-validation-summary")).toHaveTextContent("Warnings: 1");
    expect(await screen.findByTestId("bulk-validation-summary")).toHaveTextContent("Errors: 0");
    expect(screen.getByRole("button", { name: "Confirm Create" })).not.toBeDisabled();
  });

  it("invalidates a prior clean validation when a row is edited afterwards", async () => {
    loadPumps();
    await renderEditor();
    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));
    fireEvent.change(screen.getByLabelText("Pump"), { target: { value: "211-P-1A" } });
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    expect(screen.getByRole("button", { name: "Confirm Create" })).not.toBeDisabled();

    fireEvent.change(screen.getByLabelText(/^Assigned Technician for row/), { target: { value: "Someone Else" } });

    expect(screen.getByText("Not yet validated.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Confirm Create" })).toBeDisabled();
  });
});

describe("BulkPMScheduleEditor -- confirm create", () => {
  async function validRow() {
    loadPumps();
    const onCreated = vi.fn();
    await renderEditor({ onCreated });
    fireEvent.click(screen.getByRole("button", { name: "+ Add Row" }));
    fireEvent.change(screen.getByLabelText("Pump"), { target: { value: "211-P-1A" } });
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    return { onCreated };
  }

  it("calls bulkCreatePMSchedules and onCreated on success", async () => {
    bulkCreatePMSchedules.mockResolvedValue({ data: [{ client_row_id: "bulk-row-1", pm_schedule_code: "PMSCH-AAAAAAAAAAAA" }] });
    const { onCreated } = await validRow();

    fireEvent.click(screen.getByRole("button", { name: "Confirm Create" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledOnce());
    const payload = bulkCreatePMSchedules.mock.calls[0][0];
    expect(payload).toHaveLength(1);
    expect(payload[0].asset_code).toBe("211-P-1A");
  });

  it("shows a readable error and never [object Object] when the server rejects the batch", async () => {
    const error = new Error("Unknown pump: 211-P-1A");
    error.detail = [{ client_row_id: "bulk-row-1", msg: "Unknown pump: 211-P-1A" }];
    bulkCreatePMSchedules.mockRejectedValue(error);
    await validRow();

    fireEvent.click(screen.getByRole("button", { name: "Confirm Create" }));

    await waitFor(() => expect(screen.getAllByText("Unknown pump: 211-P-1A").length).toBeGreaterThan(0));
    expect(screen.queryByText(/object Object/i)).toBeNull();
    expect(screen.getByRole("button", { name: "Confirm Create" })).toBeDisabled(); // re-validation required
  });
});

// AI5R-PHASE4E5, Section F -- Manual Bulk UAT: a 10-row batch generated
// via multi-pump add, apply-to-selected exercised for every field
// Section E lists (Frequency/Start Date/Technician/Duration/Activities)
// against a SUBSET of rows, proving the untouched rows stay untouched,
// then Validate -> Confirm Create against the real (mocked) bulk
// endpoint for all 10.
describe("BulkPMScheduleEditor -- Section F 10-row Manual Bulk UAT", () => {
  const TEN_PUMPS = Array.from({ length: 10 }, (_, i) => ({
    tag_number: `900-P-${i + 1}`,
    name: `UAT Pump ${i + 1}`,
  }));

  it("adds 10 rows via multi-pump add, applies fields to selected rows only, and confirms all 10", async () => {
    getPumps.mockResolvedValue(TEN_PUMPS);
    bulkCreatePMSchedules.mockResolvedValue({
      data: TEN_PUMPS.map((p, i) => ({ client_row_id: `bulk-row-${i + 1}`, pm_schedule_code: `PMSCH-${String(i).padStart(12, "0")}` })),
    });
    const onCreated = vi.fn();
    render(<BulkPMScheduleEditor onClose={() => {}} onCreated={onCreated} existingSchedules={[]} />);
    await screen.findByTestId("bulk-pm-schedule-editor");

    // Multi-pump add: one row per selected canonical pump.
    fireEvent.click(screen.getByRole("button", { name: "+ Add Pumps..." }));
    for (const pump of TEN_PUMPS) {
      fireEvent.click(screen.getByText(`${pump.tag_number} — ${pump.name}`));
    }
    fireEvent.click(screen.getByRole("button", { name: /Add 10 Rows/ }));
    expect(screen.getAllByLabelText("Pump")).toHaveLength(10);

    // Select the first 5 rows only.
    const rowCheckboxes = screen.getAllByRole("checkbox", { name: /Select row/ });
    expect(rowCheckboxes).toHaveLength(10);
    for (const checkbox of rowCheckboxes.slice(0, 5)) {
      fireEvent.click(checkbox);
    }

    fireEvent.change(screen.getByLabelText("Apply Frequency"), { target: { value: "WEEKLY" } });
    fireEvent.change(screen.getByLabelText("Apply Start Date"), { target: { value: "2026-12-01" } });
    fireEvent.change(screen.getByLabelText("Apply Assigned Technician"), { target: { value: "Sari Wulandari" } });
    fireEvent.change(screen.getByLabelText("Apply Duration"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply to Selected" }));

    fireEvent.click(screen.getByRole("button", { name: "Apply Activities to Selected..." }));
    fireEvent.click(screen.getByLabelText("Flushing Line DE Side"));
    fireEvent.click(screen.getByRole("button", { name: "Apply Activities" }));

    const frequencies = screen.getAllByLabelText(/^Frequency for row/).map((el) => el.value);
    const dates = screen.getAllByLabelText(/^Start Date for row/).map((el) => el.value);
    const technicians = screen.getAllByLabelText(/^Assigned Technician for row/).map((el) => el.value);
    const durations = screen.getAllByLabelText(/^Duration for row/).map((el) => el.value);
    const activityCounts = screen.getAllByText(/selected$/).map((el) => el.textContent);

    // Applied fields land on exactly the first 5 selected rows...
    expect(frequencies.slice(0, 5)).toEqual(Array(5).fill("WEEKLY"));
    expect(dates.slice(0, 5)).toEqual(Array(5).fill("2026-12-01"));
    expect(technicians.slice(0, 5)).toEqual(Array(5).fill("Sari Wulandari"));
    expect(durations.slice(0, 5)).toEqual(Array(5).fill("3"));
    expect(activityCounts.slice(0, 5)).toEqual(Array(5).fill("1 selected"));
    // ...and the remaining 5 unselected rows are completely untouched.
    expect(frequencies.slice(5)).toEqual(Array(5).fill("MONTHLY"));
    expect(technicians.slice(5)).toEqual(Array(5).fill(""));
    expect(durations.slice(5)).toEqual(Array(5).fill(""));
    expect(activityCounts.slice(5)).toEqual(Array(5).fill("0 selected"));

    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    expect(await screen.findByTestId("bulk-validation-summary")).toHaveTextContent("Rows: 10");
    expect(screen.getByTestId("bulk-validation-summary")).toHaveTextContent("Errors: 0");
    expect(screen.getByRole("button", { name: "Confirm Create" })).not.toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Confirm Create" }));
    await waitFor(() => expect(onCreated).toHaveBeenCalledOnce());
    // NOTE: bulkCreatePMSchedules.mock.calls accumulates across every test
    // in this file (no afterEach clears it) -- .mock.lastCall is the call
    // THIS test made, never an earlier test's.
    expect(bulkCreatePMSchedules.mock.lastCall[0]).toHaveLength(10);
  });
});
