import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PrintButton from "./PrintButton";

describe("PrintButton", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a Print / Save as PDF button", () => {
    render(<PrintButton />);

    expect(screen.getByRole("button", { name: "Print / Save as PDF" })).toBeTruthy();
  });

  it("calls window.print when clicked", () => {
    const printSpy = vi.spyOn(window, "print").mockImplementation(() => {});

    render(<PrintButton />);
    fireEvent.click(screen.getByRole("button", { name: "Print / Save as PDF" }));

    expect(printSpy).toHaveBeenCalledTimes(1);
  });

  it("is marked no-print so it never appears in the printed output", () => {
    render(<PrintButton />);

    expect(screen.getByRole("button", { name: "Print / Save as PDF" }).className).toContain("no-print");
  });
});
