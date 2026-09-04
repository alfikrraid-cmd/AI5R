import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PMActivityFamilyChecklist from "./PMActivityFamilyChecklist";

// MWO-LTSA-PM-ACTIVITY-TAXONOMY-001

describe("PMActivityFamilyChecklist", () => {
  it("1: renders all 7 activity families", () => {
    render(<PMActivityFamilyChecklist doneMap={{}} onToggle={() => {}} />);
    for (const family of ["Flushing Line", "Quench Line", "Strainer", "Check Valve", "Reservoir", "Cooler", "Cooling Water Cooler"]) {
      expect(screen.getByTestId(`activity-family-${family}`)).toBeInTheDocument();
    }
  });

  it("Reservoir shows only a General checkbox, no DE/NDE", () => {
    render(<PMActivityFamilyChecklist doneMap={{}} onToggle={() => {}} />);
    const reservoir = screen.getByTestId("activity-family-Reservoir");
    expect(reservoir.querySelectorAll('input[type="checkbox"]')).toHaveLength(1);
    expect(screen.getByLabelText("Reservoir")).toBeInTheDocument();
  });

  it("11: no checkbox is preselected when doneMap is empty (new PM default)", () => {
    render(<PMActivityFamilyChecklist doneMap={{}} onToggle={() => {}} />);
    for (const box of screen.getAllByRole("checkbox")) {
      expect(box).not.toBeChecked();
    }
  });

  it("2: General is independently selectable (toggling it does not affect DE/NDE)", () => {
    const onToggle = vi.fn();
    render(<PMActivityFamilyChecklist doneMap={{}} onToggle={onToggle} />);
    fireEvent.click(screen.getByLabelText("Flushing Line"));
    expect(onToggle).toHaveBeenCalledWith("FLUSHING_LINE");
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("3: DE is independently selectable", () => {
    const onToggle = vi.fn();
    render(<PMActivityFamilyChecklist doneMap={{}} onToggle={onToggle} />);
    fireEvent.click(screen.getByLabelText("Flushing Line DE Side"));
    expect(onToggle).toHaveBeenCalledWith("FLUSHING_LINE_DE");
  });

  it("4: NDE is independently selectable", () => {
    const onToggle = vi.fn();
    render(<PMActivityFamilyChecklist doneMap={{}} onToggle={onToggle} />);
    fireEvent.click(screen.getByLabelText("Flushing Line NDE Side"));
    expect(onToggle).toHaveBeenCalledWith("FLUSHING_LINE_NDE");
  });

  it("5: DE and NDE can both be checked simultaneously for the same family", () => {
    render(<PMActivityFamilyChecklist doneMap={{ COOLER_DE: true, COOLER_NDE: true }} onToggle={() => {}} />);
    expect(screen.getByLabelText("Cooler DE Side")).toBeChecked();
    expect(screen.getByLabelText("Cooler NDE Side")).toBeChecked();
  });

  it("6: General + DE/NDE together does not crash or lose data -- all three reflect independently", () => {
    render(
      <PMActivityFamilyChecklist
        doneMap={{ COOLER: true, COOLER_DE: true, COOLER_NDE: false }}
        onToggle={() => {}}
      />
    );
    expect(screen.getByLabelText("Cooler")).toBeChecked();
    expect(screen.getByLabelText("Cooler DE Side")).toBeChecked();
    expect(screen.getByLabelText("Cooler NDE Side")).not.toBeChecked();
  });

  it("these are independent checkboxes, never radio buttons", () => {
    render(<PMActivityFamilyChecklist doneMap={{}} onToggle={() => {}} />);
    for (const box of screen.getAllByRole("checkbox")) {
      expect(box).toHaveAttribute("type", "checkbox");
    }
    expect(screen.queryAllByRole("radio")).toHaveLength(0);
  });

  it("7: Cooler family displays only 'Cooler' text, never WCH", () => {
    render(<PMActivityFamilyChecklist doneMap={{}} onToggle={() => {}} />);
    const cooler = screen.getByTestId("activity-family-Cooler");
    expect(cooler.textContent).toContain("Cooler");
    expect(cooler.textContent).not.toMatch(/WCH/i);
    expect(cooler.textContent).not.toMatch(/Water-Cooled Heat Exchanger/i);
  });

  it("8: Cooler and Cooling Water Cooler render as separate family sections", () => {
    render(<PMActivityFamilyChecklist doneMap={{}} onToggle={() => {}} />);
    const cooler = screen.getByTestId("activity-family-Cooler");
    const cwc = screen.getByTestId("activity-family-Cooling Water Cooler");
    expect(cooler).not.toBe(cwc);
    expect(cooler.contains(cwc)).toBe(false);
  });

  it("9: Reservoir label is the future canonical spelling", () => {
    render(<PMActivityFamilyChecklist doneMap={{}} onToggle={() => {}} />);
    expect(screen.getByLabelText("Reservoir")).toBeInTheDocument();
    expect(screen.queryByLabelText("Resevoir")).toBeNull();
  });

  it("disabled=true disables every checkbox", () => {
    render(<PMActivityFamilyChecklist doneMap={{}} onToggle={() => {}} disabled />);
    for (const box of screen.getAllByRole("checkbox")) {
      expect(box).toBeDisabled();
    }
  });
});
