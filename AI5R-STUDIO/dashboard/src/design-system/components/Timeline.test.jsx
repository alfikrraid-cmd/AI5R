import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Timeline from "./Timeline";

describe("Timeline", () => {
  it("renders each activity entry", () => {
    render(<Timeline activities={["10:01 event one", "10:02 event two"]} />);

    expect(screen.getByText("10:01 event one")).toBeTruthy();
    expect(screen.getByText("10:02 event two")).toBeTruthy();
  });

  it("renders inside a card-styled panel", () => {
    render(<Timeline activities={["a"]} />);

    expect(screen.getByTestId("panel").className).toContain("card");
  });

  it("falls back to a default demo activity list when none is provided", () => {
    render(<Timeline />);

    expect(screen.getByText(/Reality detected/)).toBeTruthy();
  });
});
