import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CreateAdHocConditionMonitoringReadingModal from "./CreateAdHocConditionMonitoringReadingModal";
import { getPumps } from "../../../api/ai5rClient";

// MWO-LTSA-CMON-ADHOC-ENTRY-001 -- isolated component tests, independent
// of ConditionMonitoring.jsx's own page-level integration coverage.

vi.mock("../../../api/ai5rClient", () => ({
  getPumps: vi.fn(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

function loadDefaults() {
  getPumps.mockResolvedValue([
    { tag_number: "641-P-5", name: "Pump 641-P-5" },
    { tag_number: "418-P-1", name: "Pump 418-P-1" },
  ]);
}

function loadDefaultsWithArea() {
  getPumps.mockResolvedValue([{ tag_number: "641-P-5", name: "Pump 641-P-5", area: "641" }]);
}

// AI5R-CMON-UX-001 -- measurement sections now default to collapsed
// (Gate 5: "should NOT initially face 38 equally-prominent inputs"), so
// tests reaching into specific measurement fields must expand first.
// Expanding changes nothing about entered values or the submitted
// payload.
function expandAllMeasurementSections() {
  for (const toggle of screen.getAllByRole("button", { expanded: false })) {
    fireEvent.click(toggle);
  }
}

describe("CreateAdHocConditionMonitoringReadingModal", () => {
  it("renders no schedule field at all, and no internal fields (reading code, provenance, workflow status, created by)", async () => {
    loadDefaults();
    render(<CreateAdHocConditionMonitoringReadingModal isOpen onClose={vi.fn()} onCreate={vi.fn()} />);
    await screen.findByLabelText("Pump");

    expect(screen.queryByLabelText("Schedule")).toBeNull();
    expect(screen.queryByText(/reading code/i)).toBeNull();
    expect(screen.queryByText(/provenance/i)).toBeNull();
    expect(screen.queryByText(/workflow status/i)).toBeNull();
    expect(screen.queryByText(/created by/i)).toBeNull();
  });

  it("uses the canonical AssetSelector backed by getPumps()", async () => {
    loadDefaults();
    render(<CreateAdHocConditionMonitoringReadingModal isOpen onClose={vi.fn()} onCreate={vi.fn()} />);

    await waitFor(() => expect(getPumps).toHaveBeenCalledOnce());
    expect(await screen.findByRole("option", { name: "641-P-5 — Pump 641-P-5" })).toBeTruthy();
  });

  it("Save Draft is disabled until both pump and reading date are set", async () => {
    loadDefaults();
    render(<CreateAdHocConditionMonitoringReadingModal isOpen onClose={vi.fn()} onCreate={vi.fn()} />);
    await screen.findByLabelText("Pump");

    expect(screen.getByRole("button", { name: "Save Draft" })).toHaveProperty("disabled", true);

    fireEvent.change(screen.getByLabelText("Pump"), { target: { value: "641-P-5" } });
    expect(screen.getByRole("button", { name: "Save Draft" })).toHaveProperty("disabled", true);

    fireEvent.change(screen.getByLabelText("Reading Date"), { target: { value: "2026-09-06" } });
    expect(screen.getByRole("button", { name: "Save Draft" })).toHaveProperty("disabled", false);
  });

  it("all measurement fields start blank -- no auto-fill, no history/ConMon-based defaults", async () => {
    loadDefaults();
    render(<CreateAdHocConditionMonitoringReadingModal isOpen onClose={vi.fn()} onCreate={vi.fn()} />);
    await screen.findByLabelText("Pump");
    expandAllMeasurementSections();

    for (const label of [
      "Mechanical Seal Temp DE", "Mechanical Seal Temp NDE",
      "Flushing Temp DE", "Flushing Temp NDE",
      "Quench Temp DE", "Quench Temp NDE",
      "Suction Pressure (bar)",
    ]) {
      expect(screen.getByLabelText(label)).toHaveProperty("value", "");
    }
    expect(screen.getByLabelText("Mechanical Seal Leak DE")).toHaveProperty("value", "");
    expect(screen.getByLabelText("Mechanical Seal Leak NDE")).toHaveProperty("value", "");
  });

  it("submits exactly the entered values -- DE-only, NDE-only, DE+NDE, and blank all preserved distinctly, leak tri-state honored, no hidden extras", async () => {
    loadDefaults();
    const onCreate = vi.fn();
    render(<CreateAdHocConditionMonitoringReadingModal isOpen onClose={vi.fn()} onCreate={onCreate} />);
    await screen.findByLabelText("Pump");
    expandAllMeasurementSections();

    fireEvent.change(screen.getByLabelText("Pump"), { target: { value: "641-P-5" } });
    fireEvent.change(screen.getByLabelText("Reading Date"), { target: { value: "2026-09-06" } });
    fireEvent.change(screen.getByLabelText("Mechanical Seal Temp DE"), { target: { value: "75.2" } });
    fireEvent.change(screen.getByLabelText("Flushing Temp NDE"), { target: { value: "61.5" } });
    fireEvent.change(screen.getByLabelText("Quench Temp DE"), { target: { value: "60" } });
    fireEvent.change(screen.getByLabelText("Quench Temp NDE"), { target: { value: "44" } });
    fireEvent.change(screen.getByLabelText("Suction Pressure (bar)"), { target: { value: "0" } });
    fireEvent.change(screen.getByLabelText("Mechanical Seal Leak DE"), { target: { value: "false" } });
    fireEvent.change(screen.getByLabelText("Finding / Notes"), { target: { value: "  routine check  " } });

    fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

    expect(onCreate).toHaveBeenCalledTimes(1);
    const payload = onCreate.mock.calls[0][0];
    expect(payload.assetCode).toBe("641-P-5");
    expect(payload.readingDate).toBe("2026-09-06");
    expect(payload.finding).toBe("routine check");
    expect(payload.measurements.mechseal_temp_de).toBe(75.2);
    expect(payload.measurements.mechseal_temp_nde).toBeNull(); // DE only -- NDE not recorded
    expect(payload.measurements.flushing_temp_de).toBeNull(); // NDE only -- DE not recorded
    expect(payload.measurements.flushing_temp_nde).toBe(61.5);
    expect(payload.measurements.quench_temp_de).toBe(60); // DE + NDE both present
    expect(payload.measurements.quench_temp_nde).toBe(44);
    expect(payload.measurements.suction_pressure).toBe(0); // explicit zero, never coerced to null
    expect(payload.measurements.suction_pressure).not.toBeNull();
    expect(payload.measurements.mechanical_seal_leak_de).toBe(false); // explicit No Leak, never null
    expect(payload.measurements.mechanical_seal_leak_nde).toBeNull(); // not recorded -- never coerced to false
    expect(payload.measurements.bearing_temp_de).toBeNull(); // untouched fields stay null, never fabricated
    expect(payload).not.toHaveProperty("conditionMonitoringScheduleCode");
    expect(payload).not.toHaveProperty("workflowStatus");
    expect(payload).not.toHaveProperty("provenance");
  });

  it("Finding left blank submits as null, never an empty string", async () => {
    loadDefaults();
    const onCreate = vi.fn();
    render(<CreateAdHocConditionMonitoringReadingModal isOpen onClose={vi.fn()} onCreate={onCreate} />);
    await screen.findByLabelText("Pump");
    expandAllMeasurementSections();
    fireEvent.change(screen.getByLabelText("Pump"), { target: { value: "641-P-5" } });
    fireEvent.change(screen.getByLabelText("Reading Date"), { target: { value: "2026-09-06" } });

    fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

    expect(onCreate.mock.calls[0][0].finding).toBeNull();
  });

  it("Cancel closes without submitting", async () => {
    loadDefaults();
    const onCreate = vi.fn();
    const onClose = vi.fn();
    render(<CreateAdHocConditionMonitoringReadingModal isOpen onClose={onClose} onCreate={onCreate} />);
    await screen.findByLabelText("Pump");

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalledOnce();
    expect(onCreate).not.toHaveBeenCalled();
  });
});

// AI5R-CMON-UX-001, Gate 3 -- persistent equipment context card.
describe("CreateAdHocConditionMonitoringReadingModal -- Selected Equipment card", () => {
  it("shows the canonical tag as the primary element once a pump is selected", async () => {
    loadDefaults();
    render(<CreateAdHocConditionMonitoringReadingModal isOpen onClose={vi.fn()} onCreate={vi.fn()} />);
    await screen.findByLabelText("Pump");

    fireEvent.change(screen.getByLabelText("Pump"), { target: { value: "641-P-5" } });

    const card = screen.getByTestId("cmon-selected-equipment-card");
    expect(card.textContent).toContain("641-P-5");
    expect(screen.queryByLabelText("Pump")).toBeNull(); // selector replaced by the card
  });

  it("displays available canonical metadata (area) when the pump record has it", async () => {
    loadDefaultsWithArea();
    render(<CreateAdHocConditionMonitoringReadingModal isOpen onClose={vi.fn()} onCreate={vi.fn()} />);
    await screen.findByLabelText("Pump");

    fireEvent.change(screen.getByLabelText("Pump"), { target: { value: "641-P-5" } });

    expect(screen.getByTestId("cmon-selected-equipment-card").textContent).toContain("641");
  });

  it("never fabricates metadata the canonical pump record does not have", async () => {
    loadDefaults(); // no `area` field on either record
    render(<CreateAdHocConditionMonitoringReadingModal isOpen onClose={vi.fn()} onCreate={vi.fn()} />);
    await screen.findByLabelText("Pump");

    fireEvent.change(screen.getByLabelText("Pump"), { target: { value: "641-P-5" } });

    expect(screen.getByTestId("cmon-selected-equipment-card").textContent).not.toContain("Area");
  });

  it("Change returns to the searchable selector without losing entered measurement values", async () => {
    loadDefaults();
    render(<CreateAdHocConditionMonitoringReadingModal isOpen onClose={vi.fn()} onCreate={vi.fn()} />);
    await screen.findByLabelText("Pump");
    fireEvent.change(screen.getByLabelText("Pump"), { target: { value: "641-P-5" } });
    expandAllMeasurementSections();
    fireEvent.change(screen.getByLabelText("Vertical Vibration DE"), { target: { value: "4.2" } });

    fireEvent.click(screen.getByRole("button", { name: "Change" }));

    expect(await screen.findByLabelText("Pump")).toBeTruthy();
    expect(screen.getByLabelText("Vertical Vibration DE")).toHaveValue(4.2);
  });
});
