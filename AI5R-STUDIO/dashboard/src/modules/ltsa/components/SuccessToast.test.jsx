import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SuccessToast from "./SuccessToast";

describe("SuccessToast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders nothing when there is no message", () => {
    render(<SuccessToast message={null} onDismiss={() => {}} />);

    expect(screen.queryByRole("status")).toBeNull();
  });

  it("renders the message when present", () => {
    render(<SuccessToast message="PM-2009 created." onDismiss={() => {}} />);

    expect(screen.getByRole("status").textContent).toContain("PM-2009 created.");
  });

  it("calls onDismiss when the dismiss button is clicked", () => {
    const onDismiss = vi.fn();
    render(<SuccessToast message="Created." onDismiss={onDismiss} />);

    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("calls onDismiss automatically after the auto-dismiss delay", () => {
    const onDismiss = vi.fn();
    render(<SuccessToast message="Created." onDismiss={onDismiss} />);

    expect(onDismiss).not.toHaveBeenCalled();

    vi.advanceTimersByTime(4000);

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
