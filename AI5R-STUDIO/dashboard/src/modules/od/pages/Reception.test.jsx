import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Reception from "./Reception";

describe("Reception page", () => {
  it("renders a single welcome call to action", () => {
    render(<Reception onEnter={() => {}} />);

    expect(screen.getByRole("heading", { name: "Welcome to your AI Company" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Begin Open Design" })).toBeTruthy();
  });

  it("calls onEnter when the user begins", () => {
    const onEnter = vi.fn();
    render(<Reception onEnter={onEnter} />);

    fireEvent.click(screen.getByRole("button", { name: "Begin Open Design" }));

    expect(onEnter).toHaveBeenCalled();
  });
});
