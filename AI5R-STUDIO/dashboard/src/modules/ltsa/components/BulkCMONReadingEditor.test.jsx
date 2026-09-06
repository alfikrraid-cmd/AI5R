import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import BulkCMONReadingEditor from "./BulkCMONReadingEditor";
import { getPumps, createAdHocConditionMonitoringReadingsBulk } from "../../../api/ai5rClient";

// MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001 -- DOM-level coverage mirroring
// BulkPMScheduleEditor.test.jsx's own split: exhaustive payload-shape/
// null-semantics cases live in cmonBulkReading.test.js's pure-function
// tests; this file proves the UI wires those functions up correctly,
// plus the Section 12 representative 10+-pump UAT and row isolation.

vi.mock("../../../api/ai5rClient", () => ({
  getPumps: vi.fn(),
  createAdHocConditionMonitoringReadingsBulk: vi.fn(),
}));

const TEN_PUMPS = Array.from({ length: 10 }, (_, i) => ({
  tag_number: `PUMP-${String.fromCharCode(65 + i)}`, // PUMP-A .. PUMP-J
  name: `Pump ${String.fromCharCode(65 + i)}`,
}));

function loadPumps(pumps = TEN_PUMPS) {
  getPumps.mockResolvedValue(pumps);
}

async function renderEditor(props = {}) {
  const onClose = props.onClose || vi.fn();
  const onCreated = props.onCreated || vi.fn();
  const utils = render(<BulkCMONReadingEditor onClose={onClose} onCreated={onCreated} />);
  await screen.findByTestId("bulk-cmon-reading-editor");
  return { ...utils, onClose, onCreated };
}

function tagToName(tag) {
  const pump = TEN_PUMPS.find((p) => p.tag_number === tag);
  return pump ? pump.name : tag;
}

function selectPumpsAndAddRows(tags) {
  fireEvent.click(screen.getByRole("button", { name: "+ Add Pumps..." }));
  for (const tag of tags) {
    fireEvent.click(screen.getByText(`${tag} — ${tagToName(tag)}`));
  }
  fireEvent.click(screen.getByRole("button", { name: new RegExp(`Add ${tags.length} Row`) }));
}

describe("BulkCMONReadingEditor -- empty state and entry", () => {
  it("starts empty with Validate and Confirm both disabled, no schedule field anywhere", async () => {
    loadPumps();
    await renderEditor();

    expect(screen.getByText(/No rows yet/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Validate" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Confirm Create" })).toBeDisabled();
    // No schedule dropdown/control anywhere -- the page subtitle itself
    // explains that no schedule is required, so this checks for the
    // absence of a schedule INPUT, not the absence of the word.
    expect(screen.queryByLabelText(/schedule/i)).toBeNull();
    expect(screen.queryByRole("combobox", { name: /schedule/i })).toBeNull();
  });
});

describe("BulkCMONReadingEditor -- multi-pump add", () => {
  it("adds one row per selected canonical pump via + Add Pumps..., never inventing a tag", async () => {
    loadPumps();
    await renderEditor();

    selectPumpsAndAddRows(["PUMP-A", "PUMP-B", "PUMP-C"]);

    expect(screen.getAllByRole("button", { name: "Remove" })).toHaveLength(3);
    const pumpSelects = screen.getAllByLabelText("Pump");
    expect(pumpSelects.map((s) => s.value).sort()).toEqual(["PUMP-A", "PUMP-B", "PUMP-C"]);
  });
});

describe("BulkCMONReadingEditor -- Section 12 representative UAT (10 pumps, heterogeneous measurements)", () => {
  it("validates, reviews, and confirms 10 rows with the exact expected outgoing payload", async () => {
    loadPumps();
    const tags = TEN_PUMPS.map((p) => p.tag_number);
    createAdHocConditionMonitoringReadingsBulk.mockResolvedValue({
      data: tags.map((tag, i) => ({ condition_monitoring_reading_code: `CMONR-BULK-${i}`, asset_code: tag })),
    });
    const { onCreated } = await renderEditor();

    selectPumpsAndAddRows(tags);
    const rows = screen.getAllByTestId(/^bulk-cmon-row-/);
    expect(rows).toHaveLength(10);

    // Common Reading Date via Select All + Apply to Selected.
    fireEvent.click(screen.getByRole("button", { name: "Select All" }));
    fireEvent.change(screen.getByLabelText("Apply Reading Date"), { target: { value: "2026-09-06" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply to Selected" }));
    for (const row of rows) {
      expect(within(row).getByLabelText(/Reading Date for row/)).toHaveValue("2026-09-06");
    }
    fireEvent.click(screen.getByRole("button", { name: "Clear Selection" }));

    function openMeasurementsFor(rowIndex) {
      fireEvent.click(within(rows[rowIndex]).getByRole("button", { name: "Edit" }));
    }
    function change(label, value) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
    }
    function closeMeasurementsModal() {
      fireEvent.click(screen.getByRole("button", { name: "Close" }));
    }

    // Pump A: Mechanical Seal Temp DE=75.2, NDE=null
    openMeasurementsFor(0);
    change("Mechanical Seal Temp DE", "75.2");
    closeMeasurementsModal();

    // Pump B: DE=null, NDE=value
    openMeasurementsFor(1);
    change("Mechanical Seal Temp NDE", "68.0");
    closeMeasurementsModal();

    // Pump C: DE=value, NDE=value
    openMeasurementsFor(2);
    change("Mechanical Seal Temp DE", "70.0");
    change("Mechanical Seal Temp NDE", "65.0");
    closeMeasurementsModal();

    // Pump D: explicit numeric 0
    openMeasurementsFor(3);
    change("Suction Pressure (bar)", "0");
    closeMeasurementsModal();

    // Pump E: Leak DE=false, Leak NDE=null (Not Recorded)
    openMeasurementsFor(4);
    change("Mechanical Seal Leak DE", "false");
    closeMeasurementsModal();

    // Pumps F-J: mixed blank/DE/NDE, left otherwise blank except one each.
    openMeasurementsFor(5);
    change("Flushing Temp DE", "40.0");
    closeMeasurementsModal();
    openMeasurementsFor(6);
    change("Flushing Temp NDE", "39.5");
    closeMeasurementsModal();
    openMeasurementsFor(7);
    change("Quench Temp DE", "60");
    change("Quench Temp NDE", "44");
    closeMeasurementsModal();
    openMeasurementsFor(8);
    change("Mechanical Seal Leak NDE", "true");
    closeMeasurementsModal();
    // Pump J (index 9): left entirely blank.

    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    expect(await screen.findByTestId("bulk-cmon-validation-summary")).toHaveTextContent(
      "Rows: 10 · Ready: 10 · Errors: 0"
    );

    fireEvent.click(screen.getByRole("button", { name: "Confirm Create" }));

    await waitFor(() => expect(createAdHocConditionMonitoringReadingsBulk).toHaveBeenCalledTimes(1));
    const sentReadings = createAdHocConditionMonitoringReadingsBulk.mock.calls[0][0];
    expect(sentReadings).toHaveLength(10);

    const [a, b, c, d, e, f, g, h, iRow, j] = sentReadings;
    expect(a.measurements.mechseal_temp_de).toBe(75.2);
    expect(a.measurements.mechseal_temp_nde).toBeNull();
    expect(b.measurements.mechseal_temp_de).toBeNull();
    expect(b.measurements.mechseal_temp_nde).toBe(68.0);
    expect(c.measurements.mechseal_temp_de).toBe(70.0);
    expect(c.measurements.mechseal_temp_nde).toBe(65.0);
    expect(d.measurements.suction_pressure).toBe(0);
    expect(d.measurements.suction_pressure).not.toBeNull();
    expect(e.measurements.mechanical_seal_leak_de).toBe(false);
    expect(e.measurements.mechanical_seal_leak_nde).toBeNull();
    expect(f.measurements.flushing_temp_de).toBe(40.0);
    expect(f.measurements.flushing_temp_nde).toBeNull();
    expect(g.measurements.flushing_temp_de).toBeNull();
    expect(g.measurements.flushing_temp_nde).toBe(39.5);
    expect(h.measurements.quench_temp_de).toBe(60);
    expect(h.measurements.quench_temp_nde).toBe(44);
    expect(iRow.measurements.mechanical_seal_leak_nde).toBe(true);
    expect(iRow.measurements.mechanical_seal_leak_de).toBeNull();
    // Pump J: every measurement stays null -- nothing auto-filled.
    expect(j.measurements.mechseal_temp_de).toBeNull();
    expect(j.measurements.mechanical_seal_leak_de).toBeNull();

    // Row isolation, asserted globally: no row's edit leaked into another.
    for (let idx = 0; idx < sentReadings.length; idx++) {
      expect(sentReadings[idx].asset_code).toBe(tags[idx]);
      expect(sentReadings[idx].reading_date).toBe("2026-09-06");
    }

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith([
      expect.objectContaining({ condition_monitoring_reading_code: "CMONR-BULK-0" }),
      expect.objectContaining({ condition_monitoring_reading_code: "CMONR-BULK-1" }),
      expect.objectContaining({ condition_monitoring_reading_code: "CMONR-BULK-2" }),
      expect.objectContaining({ condition_monitoring_reading_code: "CMONR-BULK-3" }),
      expect.objectContaining({ condition_monitoring_reading_code: "CMONR-BULK-4" }),
      expect.objectContaining({ condition_monitoring_reading_code: "CMONR-BULK-5" }),
      expect.objectContaining({ condition_monitoring_reading_code: "CMONR-BULK-6" }),
      expect.objectContaining({ condition_monitoring_reading_code: "CMONR-BULK-7" }),
      expect.objectContaining({ condition_monitoring_reading_code: "CMONR-BULK-8" }),
      expect.objectContaining({ condition_monitoring_reading_code: "CMONR-BULK-9" }),
    ]));
    expect(createAdHocConditionMonitoringReadingsBulk).toHaveBeenCalledTimes(1); // one atomic call, never ten
  }, 15000);
});

describe("BulkCMONReadingEditor -- edit invalidates validation", () => {
  it("editing a row after Validate resets the summary until Validate is re-run", async () => {
    loadPumps();
    await renderEditor();
    selectPumpsAndAddRows(["PUMP-A"]);
    fireEvent.change(screen.getByLabelText(/Reading Date for row/), { target: { value: "2026-09-06" } });

    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    await screen.findByTestId("bulk-cmon-validation-summary");

    fireEvent.change(screen.getByLabelText(/Finding for row/), { target: { value: "changed" } });

    expect(screen.queryByTestId("bulk-cmon-validation-summary")).toBeNull();
    expect(screen.getByText("Not yet validated.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Confirm Create" })).toBeDisabled();
  });
});

describe("BulkCMONReadingEditor -- no implicit measurement propagation", () => {
  it("Apply to Selected only ever changes Reading Date, never measurements or Finding", async () => {
    loadPumps();
    await renderEditor();
    selectPumpsAndAddRows(["PUMP-A", "PUMP-B"]);
    const rows = screen.getAllByTestId(/^bulk-cmon-row-/);

    fireEvent.click(within(rows[0]).getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Mechanical Seal Temp DE"), { target: { value: "75.2" } });
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    fireEvent.change(within(rows[0]).getByLabelText(/Finding for row/), { target: { value: "Row A note" } });

    fireEvent.click(screen.getByRole("button", { name: "Select All" }));
    fireEvent.change(screen.getByLabelText("Apply Reading Date"), { target: { value: "2026-09-06" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply to Selected" }));

    // Reading Date propagated to the selected row B...
    expect(within(rows[1]).getByLabelText(/Reading Date for row/)).toHaveValue("2026-09-06");
    // ...but row A's measurements/Finding never leaked to row B.
    expect(within(rows[1]).getByLabelText(/Finding for row/)).toHaveValue("");
    fireEvent.click(within(rows[1]).getByRole("button", { name: "Edit" }));
    expect(screen.getByLabelText("Mechanical Seal Temp DE")).toHaveValue(null);
  });

  it("offers no bulk measurement-copy action at all", async () => {
    loadPumps();
    await renderEditor();
    selectPumpsAndAddRows(["PUMP-A", "PUMP-B"]);
    fireEvent.click(screen.getByRole("button", { name: "Select All" }));

    expect(screen.queryByRole("button", { name: /Apply Measurements?/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Apply Activities/i })).toBeNull();
    // Only one Apply action exists at all, and it is Reading-Date-only.
    expect(screen.getAllByRole("button", { name: /^Apply to Selected$/ })).toHaveLength(1);
  });
});

describe("BulkCMONReadingEditor -- error surfacing", () => {
  it("surfaces a verbatim backend error and re-invalidates, without losing entered rows", async () => {
    loadPumps();
    createAdHocConditionMonitoringReadingsBulk.mockRejectedValueOnce(new Error("pump tag(s) unknown/ambiguous"));
    await renderEditor();
    selectPumpsAndAddRows(["PUMP-A"]);
    fireEvent.change(screen.getByLabelText(/Reading Date for row/), { target: { value: "2026-09-06" } });
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm Create" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("pump tag(s) unknown/ambiguous");
    expect(screen.getByLabelText("Pump")).toHaveValue("PUMP-A"); // row not lost
    expect(screen.getByRole("button", { name: "Confirm Create" })).toBeDisabled(); // re-validation required
  });
});
