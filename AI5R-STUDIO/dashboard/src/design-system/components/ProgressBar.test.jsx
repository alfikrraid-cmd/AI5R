import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ProgressBar from "./ProgressBar";

describe("ProgressBar", () => {
  it("renders a fill width proportional to value/max", () => {
    render(<ProgressBar value={30} max={100} label="Build" />);

    const fill = screen.getByTestId("progress-bar-fill");
    expect(fill.style.width).toBe("30%");
  });

  it("clamps value above max to 100%", () => {
    render(<ProgressBar value={150} max={100} />);

    expect(screen.getByTestId("progress-bar-fill").style.width).toBe("100%");
  });

  it("clamps negative value to 0%", () => {
    render(<ProgressBar value={-10} max={100} />);

    expect(screen.getByTestId("progress-bar-fill").style.width).toBe("0%");
  });

  it("renders an optional label", () => {
    render(<ProgressBar value={50} max={100} label="Loading" />);

    expect(screen.getByText("Loading")).toBeTruthy();
  });
});
