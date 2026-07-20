import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import RecentActivityFeed from "./RecentActivityFeed";

const ACTIVITIES = [
  {
    id: "WO-1001",
    type: "WO",
    date: "2026-07-18",
    title: "Seal replacement — repeat failures",
    status: "OPEN",
  },
  {
    id: "PM-2006",
    type: "PM",
    date: "2026-07-19",
    title: "Daily Operator Walkdown",
    status: "DUE_SOON",
  },
];

describe("RecentActivityFeed", () => {
  it("renders a row per activity with type and status badges", () => {
    render(<RecentActivityFeed activities={ACTIVITIES} />);

    expect(screen.getByRole("heading", { name: "Recent Activities" })).toBeTruthy();
    expect(screen.getByText("WO-1001")).toBeTruthy();
    expect(screen.getByText("Work Order")).toBeTruthy();
    expect(screen.getByText("PM-2006")).toBeTruthy();
    expect(screen.getByText("Due Soon")).toBeTruthy();
  });

  it("renders an empty state when there is no activity", () => {
    render(<RecentActivityFeed activities={[]} />);

    expect(screen.getByText(/no recent activity/i)).toBeTruthy();
  });
});
