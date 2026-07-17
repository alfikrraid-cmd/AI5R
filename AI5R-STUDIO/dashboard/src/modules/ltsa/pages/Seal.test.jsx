import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Seal from "./Seal";
import sampleSeals from "../data/sampleSeals";

describe("Seal workspace page", () => {
  it("renders the page header", () => {
    render(<Seal />);

    expect(screen.getByRole("heading", { name: "Seal Workspace" })).toBeTruthy();
  });

  it("renders all 10 sample seals in the registry table", () => {
    render(<Seal />);

    sampleSeals.forEach((seal) => {
      expect(screen.getByText(seal.code)).toBeTruthy();
    });
  });

  it("shows an empty state in the detail panel before any seal is selected", () => {
    render(<Seal />);

    expect(screen.getByText(/no seal selected/i)).toBeTruthy();
  });

  it("shows the selected seal's detail when a registry row is clicked", () => {
    render(<Seal />);

    fireEvent.click(screen.getByText("SC-003"));

    expect(screen.getByRole("heading", { name: "Flowserve ISC2" })).toBeTruthy();
  });

  it("filters the registry table by search text", () => {
    render(<Seal />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "AESSEAL" } });

    expect(screen.getByText("SC-005")).toBeTruthy();
    expect(screen.queryByText("SC-001")).toBeNull();
  });

  it("filters the registry table by status", () => {
    render(<Seal />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "FAULT" } });

    expect(screen.getByText("SC-007")).toBeTruthy();
    expect(screen.queryByText("SC-001")).toBeNull();
  });
});
