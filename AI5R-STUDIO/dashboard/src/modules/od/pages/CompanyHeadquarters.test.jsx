import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CompanyHeadquarters from "./CompanyHeadquarters";

const blueprint = {
  blueprintId: "BLUEPRINT-1",
  businessIdentity: "Acme Pump Services",
  objective: "no more missed service calls",
  context: "help me run my business",
  capturedAt: "2026-07-21T00:00:00.000Z",
};

describe("CompanyHeadquarters page", () => {
  it("renders the company identity from the sealed blueprint", () => {
    render(
      <CompanyHeadquarters
        blueprint={blueprint}
        hasSeenBriefing
        onDismissBriefing={() => {}}
        onNavigate={() => {}}
      />
    );

    expect(screen.getByRole("heading", { name: "Acme Pump Services" })).toBeTruthy();
  });

  it("shows the Executive Briefing the first time", () => {
    render(
      <CompanyHeadquarters
        blueprint={blueprint}
        hasSeenBriefing={false}
        onDismissBriefing={() => {}}
        onNavigate={() => {}}
      />
    );

    expect(screen.getByTestId("modal")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Executive Briefing" })).toBeTruthy();
  });

  it("does not show the Executive Briefing once it has been seen", () => {
    render(
      <CompanyHeadquarters
        blueprint={blueprint}
        hasSeenBriefing
        onDismissBriefing={() => {}}
        onNavigate={() => {}}
      />
    );

    expect(screen.queryByTestId("modal")).toBeNull();
  });

  it("dismisses the briefing when closed", () => {
    const onDismissBriefing = vi.fn();
    render(
      <CompanyHeadquarters
        blueprint={blueprint}
        hasSeenBriefing={false}
        onDismissBriefing={onDismissBriefing}
        onNavigate={() => {}}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Close" }));

    expect(onDismissBriefing).toHaveBeenCalled();
  });

  it("renders all five executives, present and available", () => {
    render(
      <CompanyHeadquarters
        blueprint={blueprint}
        hasSeenBriefing
        onDismissBriefing={() => {}}
        onNavigate={() => {}}
      />
    );

    ["Ra'id", "Graham", "Aurora", "Atlas", "Sophia"].forEach((name) => {
      expect(screen.getByRole("heading", { name })).toBeTruthy();
    });
    expect(screen.getAllByText("Available")).toHaveLength(5);
  });

  it("shows an empty state for artifacts and a sealed entry in the timeline", () => {
    render(
      <CompanyHeadquarters
        blueprint={blueprint}
        hasSeenBriefing
        onDismissBriefing={() => {}}
        onNavigate={() => {}}
      />
    );

    expect(screen.getByText("Nothing produced yet")).toBeTruthy();
    expect(screen.getByText(/Business Blueprint sealed/)).toBeTruthy();
  });

  it("renders the suggested next actions", () => {
    render(
      <CompanyHeadquarters
        blueprint={blueprint}
        hasSeenBriefing
        onDismissBriefing={() => {}}
        onNavigate={() => {}}
      />
    );

    expect(screen.getByRole("heading", { name: "Suggested Next Actions" })).toBeTruthy();
  });
});
