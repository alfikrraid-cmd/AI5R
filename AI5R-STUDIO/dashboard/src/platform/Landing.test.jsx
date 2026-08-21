import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Landing from "./Landing";
import { PlatformContext } from "./PlatformContext";

const applications = Object.freeze([
  Object.freeze({
    applicationId: "platform-home",
    displayName: "AI5ROS",
    status: "active",
  }),
  Object.freeze({
    applicationId: "ltsa",
    displayName: "LTSA",
    status: "active",
  }),
  Object.freeze({
    applicationId: "auditor",
    displayName: "Auditor",
    status: "planned",
  }),
]);

function renderLanding(onNavigateApplication = vi.fn()) {
  render(
    <PlatformContext.Provider value={{ applications }}>
      <Landing onNavigateApplication={onNavigateApplication} />
    </PlatformContext.Provider>
  );
  return onNavigateApplication;
}

describe("Landing", () => {
  it("renders available applications from PlatformRegistry output", () => {
    renderLanding();

    expect(screen.getByRole("heading", { level: 1, name: "AI5ROS" })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 3, name: "LTSA" })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 3, name: "Auditor" })).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 3, name: "AI5ROS" })).toBeNull();
  });

  it("disables unavailable applications", () => {
    renderLanding();
    const buttons = screen.getAllByRole("button", { name: "Open" });

    expect(buttons[0].disabled).toBe(false);
    expect(buttons[1].disabled).toBe(true);
  });

  it("delegates available application navigation", () => {
    const onNavigateApplication = renderLanding();

    fireEvent.click(screen.getAllByRole("button", { name: "Open" })[0]);

    expect(onNavigateApplication).toHaveBeenCalledWith("ltsa");
  });

  it("MWO-LTSA-DEMO-READINESS-CLOSURE-001: application cards use the styled 'card' class, not the undefined 'metric-card' class", () => {
    renderLanding();

    const card = screen.getByRole("heading", { level: 3, name: "LTSA" }).closest("article");
    expect(card.className).toBe("card");
  });

  it("MWO-LTSA-DEMO-READINESS-CLOSURE-001: 'Open' uses the styled design-system Button, not a bare unstyled button", () => {
    renderLanding();

    const openButton = screen.getAllByRole("button", { name: "Open" })[0];
    expect(openButton.className).toContain("ds-button");
  });
});
