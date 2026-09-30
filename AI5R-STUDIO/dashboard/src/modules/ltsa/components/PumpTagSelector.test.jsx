import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import PumpTagSelector from "./PumpTagSelector";

const pumps = [{ tag_number: "940-P-1B", area: "Area 940" }, { tag_number: "211-P-16", area: "Area 211" }, { tag_number: "702-P-4A", area: "Area 702" }];

describe("PumpTagSelector", () => {
  it("shows current route tag and supports case-insensitive partial search", () => {
    render(<PumpTagSelector pumps={pumps} currentTag="940-P-1B" onSelect={vi.fn()} />);
    expect(screen.getByText("940-P-1B")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button"));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "p-16" } });
    expect(screen.getByRole("option", { name: /211-P-16/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /702-P-4A/ })).not.toBeInTheDocument();
  });

  it("navigates on selection and supports empty, loading, and keyboard selection", () => {
    const onSelect = vi.fn();
    render(<PumpTagSelector pumps={pumps} currentTag="940-P-1B" onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button"));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "does-not-exist" } });
    expect(screen.getByRole("status")).toHaveTextContent("No pumps match");
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "211" } });
    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith("211-P-16");
    const { unmount } = render(<PumpTagSelector loading pumps={[]} currentTag="940-P-1B" onSelect={onSelect} />);
    fireEvent.click(screen.getAllByRole("button")[1]);
    expect(screen.getByRole("status")).toHaveTextContent("Loading pumps");
    unmount();
  });

  it("limits visible results to 20 while searching the complete registry", () => {
    const manyPumps = Array.from({ length: 21 }, (_, index) => ({ tag_number: `940-P-${index + 1}B` }));
    render(<PumpTagSelector pumps={manyPumps} currentTag="940-P-1B" onSelect={vi.fn()} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getAllByRole("option")).toHaveLength(20);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "940-P-21B" } });
    expect(screen.getByRole("option", { name: "940-P-21B" })).toBeInTheDocument();
  });

  it("reports an API error without exposing a misleading empty registry", () => {
    render(<PumpTagSelector pumps={[]} currentTag="940-P-1B" error={new Error("offline")} onSelect={vi.fn()} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("alert")).toHaveTextContent("Unable to load pumps");
  });

  it("passes the authoritative tag to the Asset 360 navigation callback", () => {
    const onSelect = vi.fn();
    render(<PumpTagSelector pumps={[{ tag_number: "101-P-10A" }, { tag_number: "211-P-16A" }]} currentTag="940-P-1B" onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button"));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "101-P-10A" } });
    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith("101-P-10A");
    expect(onSelect).not.toHaveBeenCalledWith("/ltsa/pump");
  });

  it("does not invoke navigation for an invalid registry item", () => {
    const onSelect = vi.fn();
    render(<PumpTagSelector pumps={[{ tag_number: null }]} currentTag="940-P-1B" onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(onSelect).not.toHaveBeenCalled();
  });
});
