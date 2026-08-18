import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CreateConditionMonitoringReadingModal from "./CreateConditionMonitoringReadingModal";

// MWO-LTSA-PM-CM-REVIEW-PRE-PUSH-CLOSURE-001 -- proves TAP_ENGINEER can
// manually enter every canonical golden CMON measurement (migration 014)
// from the Create form, with correct blank/zero/DE-NDE/leak-tri-state
// semantics. First dedicated test file for this modal.
const SCHEDULES = [{ id: "CMON-SCHED-001", equipmentTag: "641-P-5" }];

function renderModal(onCreate = vi.fn()) {
  render(
    <CreateConditionMonitoringReadingModal isOpen onClose={vi.fn()} onCreate={onCreate} schedules={SCHEDULES} />
  );
  fireEvent.change(screen.getByLabelText("Schedule"), { target: { value: "CMON-SCHED-001" } });
  return onCreate;
}

describe("CreateConditionMonitoringReadingModal -- golden CMON measurement entry", () => {
  it("submits null (not 0) for every measurement left blank", () => {
    const onCreate = vi.fn();
    renderModal(onCreate);

    fireEvent.click(screen.getByRole("button", { name: "Create Reading" }));

    const payload = onCreate.mock.calls[0][0];
    expect(payload.measurements.suction_pressure).toBeNull();
    expect(payload.measurements.discharge_pressure).toBeNull();
    expect(payload.measurements.bearing_temp_de).toBeNull();
    expect(payload.measurements.bearing_temp_nde).toBeNull();
    expect(payload.measurements.motor_current).toBeNull();
    expect(payload.measurements.mechanical_seal_leak_de).toBeNull();
    expect(payload.measurements.mechanical_seal_leak_nde).toBeNull();
  });

  it("captures every migration-014 field explicitly entered, DE and NDE kept separate", () => {
    const onCreate = vi.fn();
    renderModal(onCreate);

    fireEvent.change(screen.getByLabelText("Suction Pressure (bar)"), { target: { value: "3.2" } });
    fireEvent.change(screen.getByLabelText("Discharge Pressure (bar)"), { target: { value: "11.4" } });
    fireEvent.change(screen.getByLabelText("Motor Current (A)"), { target: { value: "22.1" } });
    fireEvent.change(screen.getByLabelText("Bearing Temp DE"), { target: { value: "61" } });
    fireEvent.change(screen.getByLabelText("Bearing Temp NDE"), { target: { value: "58" } });
    fireEvent.change(screen.getByLabelText("Vertical Vibration DE"), { target: { value: "2.1" } });
    // NDE for vertical vibration intentionally left blank.

    fireEvent.click(screen.getByRole("button", { name: "Create Reading" }));

    const { measurements } = onCreate.mock.calls[0][0];
    expect(measurements.suction_pressure).toBe(3.2);
    expect(measurements.discharge_pressure).toBe(11.4);
    expect(measurements.motor_current).toBe(22.1);
    expect(measurements.bearing_temp_de).toBe(61);
    expect(measurements.bearing_temp_nde).toBe(58);
    expect(measurements.vertical_vibration_de).toBe(2.1);
    expect(measurements.vertical_vibration_nde).toBeNull();
  });

  it("preserves an explicitly entered zero (never coerced to null)", () => {
    const onCreate = vi.fn();
    renderModal(onCreate);

    fireEvent.change(screen.getByLabelText("Motor Current (A)"), { target: { value: "0" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Reading" }));

    expect(onCreate.mock.calls[0][0].measurements.motor_current).toBe(0);
  });

  it("leak status defaults to Not Recorded, never fabricates No Leak from a blank selection", () => {
    const onCreate = vi.fn();
    renderModal(onCreate);

    fireEvent.click(screen.getByRole("button", { name: "Create Reading" }));

    const { measurements } = onCreate.mock.calls[0][0];
    expect(measurements.mechanical_seal_leak_de).toBeNull();
    expect(measurements.mechanical_seal_leak_nde).toBeNull();
  });

  it("captures leak DE and NDE as independent tri-state values", () => {
    const onCreate = vi.fn();
    renderModal(onCreate);

    fireEvent.change(screen.getByLabelText("Mechanical Seal Leak DE"), { target: { value: "true" } });
    fireEvent.change(screen.getByLabelText("Mechanical Seal Leak NDE"), { target: { value: "false" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Reading" }));

    const { measurements } = onCreate.mock.calls[0][0];
    expect(measurements.mechanical_seal_leak_de).toBe(true);
    expect(measurements.mechanical_seal_leak_nde).toBe(false);
  });

  it("resets the full form after a successful create", () => {
    const onCreate = vi.fn();
    renderModal(onCreate);

    fireEvent.change(screen.getByLabelText("Motor Current (A)"), { target: { value: "22.1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Reading" }));

    expect(screen.getByLabelText("Motor Current (A)")).toHaveProperty("value", "");
  });
});
