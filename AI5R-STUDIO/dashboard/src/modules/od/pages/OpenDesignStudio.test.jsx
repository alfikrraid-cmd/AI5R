import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import OpenDesignStudio from "./OpenDesignStudio";

function fillAndContinue(labelText, value) {
  fireEvent.change(screen.getByLabelText(labelText), { target: { value } });
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
}

describe("OpenDesignStudio page", () => {
  it("starts on Mission Input with Continue disabled until something is typed", () => {
    render(<OpenDesignStudio onComplete={() => {}} />);

    expect(screen.getByLabelText("Mission Input")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Continue" }).disabled).toBe(true);
  });

  it("walks through Mission Input, both guided elaboration steps, and Review, then seals a blueprint", () => {
    const onComplete = vi.fn();
    render(<OpenDesignStudio onComplete={onComplete} />);

    fillAndContinue("Mission Input", "help me run my pump maintenance business");
    fillAndContinue("Who is this business, and what industry are you in?", "a pump maintenance company");
    fillAndContinue("What does success look like once this is working?", "no more missed service calls");

    expect(screen.getByRole("heading", { name: "Review" })).toBeTruthy();
    expect(screen.getByText(/help me run my pump maintenance business/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Confirm & Seal Blueprint" }));

    expect(onComplete).toHaveBeenCalledTimes(1);
    const blueprint = onComplete.mock.calls[0][0];
    expect(blueprint.context).toBe("help me run my pump maintenance business");
    expect(blueprint.businessIdentity).toBe("a pump maintenance company");
    expect(blueprint.objective).toBe("no more missed service calls");
    expect(blueprint.blueprintId).toMatch(/^BLUEPRINT-/);
  });
});
