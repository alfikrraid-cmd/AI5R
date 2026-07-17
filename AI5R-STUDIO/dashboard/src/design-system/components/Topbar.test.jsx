import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Topbar from "./Topbar";

describe("Topbar", () => {
  it("renders the brand/title", () => {
    render(<Topbar title="AI5R Studio" />);

    expect(screen.getByText("AI5R Studio")).toBeTruthy();
  });

  it("renders optional actions", () => {
    render(<Topbar title="AI5R Studio" actions={<button>Sign out</button>} />);

    expect(screen.getByRole("button", { name: "Sign out" })).toBeTruthy();
  });
});
