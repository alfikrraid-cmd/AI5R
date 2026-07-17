import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Panel from "./Panel";

describe("Panel", () => {
  it("renders its children inside a card-styled container", () => {
    render(
      <Panel>
        <p>Content</p>
      </Panel>
    );

    expect(screen.getByText("Content")).toBeTruthy();
    expect(screen.getByTestId("panel").className).toContain("card");
  });

  it("applies an additional className when provided", () => {
    render(<Panel className="extra">child</Panel>);

    expect(screen.getByTestId("panel").className).toContain("extra");
  });
});
