import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Table from "./Table";

describe("Table", () => {
  it("renders one row per item, in label/value cells", () => {
    render(
      <Table
        rows={[
          { label: "Total Events", value: 3 },
          { label: "Task Events", value: 1 },
        ]}
      />
    );

    expect(screen.getByText("Total Events")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("Task Events")).toBeTruthy();
    expect(screen.getByText("1")).toBeTruthy();
  });

  it("renders an empty table body when given no rows", () => {
    render(<Table rows={[]} />);

    expect(screen.getByRole("table")).toBeTruthy();
    expect(screen.queryAllByRole("row").length).toBe(0);
  });

  describe("columns/data mode (multi-column tabular data)", () => {
    const columns = [
      { key: "code", header: "Code" },
      { key: "name", header: "Name" },
    ];

    const data = [
      { code: "P-101", name: "Boiler Feed Pump 1" },
      { code: "P-102", name: "Boiler Feed Pump 2" },
    ];

    it("renders a header row from columns and a body row per data item", () => {
      render(<Table columns={columns} data={data} rowKey="code" />);

      expect(screen.getByRole("columnheader", { name: "Code" })).toBeTruthy();
      expect(screen.getByRole("columnheader", { name: "Name" })).toBeTruthy();
      expect(screen.getByText("P-101")).toBeTruthy();
      expect(screen.getByText("Boiler Feed Pump 2")).toBeTruthy();
    });

    it("calls onRowClick with the clicked row's data", () => {
      const onRowClick = vi.fn();
      render(<Table columns={columns} data={data} rowKey="code" onRowClick={onRowClick} />);

      fireEvent.click(screen.getByText("P-101"));

      expect(onRowClick).toHaveBeenCalledWith(data[0]);
    });

    it("marks the selected row via aria-selected", () => {
      render(
        <Table columns={columns} data={data} rowKey="code" selectedKey="P-102" onRowClick={() => {}} />
      );

      const rows = screen.getAllByRole("row");
      expect(rows[2].getAttribute("aria-selected")).toBe("true");
      expect(rows[1].getAttribute("aria-selected")).toBe("false");
    });
  });
});
