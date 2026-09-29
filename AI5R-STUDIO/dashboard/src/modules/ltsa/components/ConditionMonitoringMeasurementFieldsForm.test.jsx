import "@testing-library/jest-dom";
import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ConditionMonitoringMeasurementFieldsForm from "./ConditionMonitoringMeasurementFieldsForm";
import {
  MEASUREMENT_PAIR_FIELDS,
  MEASUREMENT_SINGLE_FIELDS,
  emptyMeasurementFormValues,
} from "../utils/conditionMonitoringMeasurementFields";

// AI5R-CMON-UX-001 -- proves the grouped/collapsible presentation change
// never drops a field, never renames a payload key, and never loses an
// entered value on collapse/expand. Uses only synthetic measurement
// values.

function Harness({ initial = emptyMeasurementFormValues() }) {
  const [measurements, setMeasurements] = useState(initial);
  function onFieldChange(name) {
    return (event) => setMeasurements((current) => ({ ...current, [name]: event.target.value }));
  }
  return <ConditionMonitoringMeasurementFieldsForm measurements={measurements} onFieldChange={onFieldChange} idPrefix="test" />;
}

function expandAll() {
  for (const toggle of screen.getAllByRole("button", { expanded: false })) {
    fireEvent.click(toggle);
  }
}

describe("ConditionMonitoringMeasurementFieldsForm -- grouping", () => {
  it("represents every active canonical pair and single field once collapsed sections are expanded, and omits vibration", () => {
    render(<Harness />);
    expandAll();

    const activePairFields = MEASUREMENT_PAIR_FIELDS.filter((field) => !field.group.includes("Vibration"));
    for (const field of activePairFields) {
      expect(screen.getByLabelText(`${field.group} DE`)).toBeTruthy();
      expect(screen.getByLabelText(`${field.group} NDE`)).toBeTruthy();
    }
    for (const field of MEASUREMENT_SINGLE_FIELDS) {
      expect(screen.getByLabelText(`${field.label} (${field.unit})`)).toBeTruthy();
    }
    expect(screen.getByLabelText("Mechanical Seal Leak DE")).toBeTruthy();
    expect(screen.getByLabelText("Mechanical Seal Leak NDE")).toBeTruthy();
    expect(screen.getByLabelText("Pump Operating State")).toBeTruthy();

    // Proves vibration fields are not present in active UI
    for (const vField of [
      "Vertical Vibration DE",
      "Vertical Vibration NDE",
      "Horizontal Vibration DE",
      "Horizontal Vibration NDE",
      "Axial Vibration DE",
      "Axial Vibration NDE",
    ]) {
      expect(screen.queryByLabelText(vField)).toBeNull();
    }
  });

  it("groups fields into the expected active named sections and contains no Vibration section", () => {
    render(<Harness />);

    for (const title of ["Bearing Temperature", "Mechanical Seal / Gland", "Flushing / Quench", "Cooling", "Process Conditions"]) {
      expect(screen.getByRole("button", { name: new RegExp(`^${title}`) })).toBeTruthy();
    }
    expect(screen.queryByRole("button", { name: /^Vibration/ })).toBeNull();
  });

  it("units remain exactly as the canonical catalog defines them", () => {
    render(<Harness />);
    expandAll();

    expect(screen.getByLabelText("Bearing Temp DE").closest("div").textContent).not.toContain("mm/s");
    expect(screen.getByText("Bearing Temp (°C)")).toBeTruthy();
    expect(screen.getByText("Motor Current (A)")).toBeTruthy();
    expect(screen.getByText("Suction Pressure (bar)")).toBeTruthy();
  });

  it("fields start collapsed (Gate 5): the engineer does not initially face every input", () => {
    render(<Harness />);

    expect(screen.queryByLabelText("Bearing Temp DE")).toBeNull();
    expect(screen.getAllByRole("button", { expanded: false }).length).toBeGreaterThan(0);
  });

  it("collapsing a section after entering a value does not clear it", () => {
    render(<Harness />);
    expandAll();

    fireEvent.change(screen.getByLabelText("Bearing Temp DE"), { target: { value: "65.5" } });
    const sectionToggle = screen.getByRole("button", { name: /^Bearing Temperature/ });

    fireEvent.click(sectionToggle); // collapse
    fireEvent.click(sectionToggle); // expand again

    expect(screen.getByLabelText("Bearing Temp DE")).toHaveValue(65.5);
  });

  it("a section header shows a recorded-value count once fields are filled", () => {
    render(<Harness />);
    expandAll();

    fireEvent.change(screen.getByLabelText("Bearing Temp DE"), { target: { value: "65.5" } });
    const sectionToggle = screen.getByRole("button", { name: /^Bearing Temperature/ });
    fireEvent.click(sectionToggle); // collapse

    expect(sectionToggle.textContent).toContain("1 reading");
  });

  it("renders Drive End (DE) and Non-Drive End (NDE) table headers in paired sections", () => {
    render(<Harness />);
    expandAll();

    expect(screen.getAllByText("Drive End (DE)").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Non-Drive End (NDE)").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Parameter").length).toBeGreaterThan(0);
  });

  it("toggles all sections via the Expand All / Collapse All action", () => {
    render(<Harness />);

    // Initially collapsed
    expect(screen.queryByLabelText("Bearing Temp DE")).toBeNull();

    // Click Expand All
    const toggleAllBtn = screen.getByRole("button", { name: "Expand All ▾" });
    fireEvent.click(toggleAllBtn);

    expect(screen.getByLabelText("Bearing Temp DE")).toBeInTheDocument();
    expect(screen.queryByLabelText("Vertical Vibration DE")).toBeNull();
    expect(screen.getByRole("button", { name: "Collapse All ▴" })).toBeInTheDocument();

    // Click Collapse All
    fireEvent.click(screen.getByRole("button", { name: "Collapse All ▴" }));
    expect(screen.queryByLabelText("Bearing Temp DE")).toBeNull();
  });
});
