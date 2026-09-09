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
  it("represents every canonical pair and single field once collapsed sections are expanded", () => {
    render(<Harness />);
    expandAll();

    for (const field of MEASUREMENT_PAIR_FIELDS) {
      expect(screen.getByLabelText(`${field.group} DE`)).toBeTruthy();
      expect(screen.getByLabelText(`${field.group} NDE`)).toBeTruthy();
    }
    for (const field of MEASUREMENT_SINGLE_FIELDS) {
      expect(screen.getByLabelText(`${field.label} (${field.unit})`)).toBeTruthy();
    }
    expect(screen.getByLabelText("Mechanical Seal Leak DE")).toBeTruthy();
    expect(screen.getByLabelText("Mechanical Seal Leak NDE")).toBeTruthy();
    expect(screen.getByLabelText("Pump Operating State")).toBeTruthy();
  });

  it("groups fields into the expected named sections", () => {
    render(<Harness />);

    for (const title of ["Vibration", "Bearing Temperature", "Mechanical Seal / Gland", "Flushing / Quench", "Cooling", "Process Conditions"]) {
      expect(screen.getByRole("button", { name: new RegExp(`^${title}`) })).toBeTruthy();
    }
  });

  it("units remain exactly as the canonical catalog defines them", () => {
    render(<Harness />);
    expandAll();

    expect(screen.getByLabelText("Vertical Vibration DE").closest("div").textContent).not.toContain("°C");
    expect(screen.getByText("Vertical Vibration (mm/s)")).toBeTruthy();
    expect(screen.getByText("Motor Current (A)")).toBeTruthy();
    expect(screen.getByText("Suction Pressure (bar)")).toBeTruthy();
  });

  it("fields start collapsed (Gate 5): the engineer does not initially face every input", () => {
    render(<Harness />);

    expect(screen.queryByLabelText("Vertical Vibration DE")).toBeNull();
    expect(screen.getAllByRole("button", { expanded: false }).length).toBeGreaterThan(0);
  });

  it("collapsing a section after entering a value does not clear it", () => {
    render(<Harness />);
    expandAll();

    fireEvent.change(screen.getByLabelText("Vertical Vibration DE"), { target: { value: "4.2" } });
    const sectionToggle = screen.getByRole("button", { name: /^Vibration/ });

    fireEvent.click(sectionToggle); // collapse
    fireEvent.click(sectionToggle); // expand again

    expect(screen.getByLabelText("Vertical Vibration DE")).toHaveValue(4.2);
  });

  it("a section header shows a recorded-value count once fields are filled", () => {
    render(<Harness />);
    expandAll();

    fireEvent.change(screen.getByLabelText("Vertical Vibration DE"), { target: { value: "4.2" } });
    const sectionToggle = screen.getByRole("button", { name: /^Vibration/ });
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
    expect(screen.queryByLabelText("Vertical Vibration DE")).toBeNull();

    // Click Expand All
    const toggleAllBtn = screen.getByRole("button", { name: "Expand All ▾" });
    fireEvent.click(toggleAllBtn);

    expect(screen.getByLabelText("Vertical Vibration DE")).toBeInTheDocument();
    expect(screen.getByLabelText("Bearing Temp DE")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Collapse All ▴" })).toBeInTheDocument();

    // Click Collapse All
    fireEvent.click(screen.getByRole("button", { name: "Collapse All ▴" }));
    expect(screen.queryByLabelText("Vertical Vibration DE")).toBeNull();
  });
});
