import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AssetsAttentionPanel from "./AssetsAttentionPanel";

function topRisk(overrides = {}) {
  return {
    tag_number: "641-P-5",
    rule_code: "REC_CRITICAL_CM",
    title: "Immediate Inspection",
    priority: 100,
    action: "Dispatch a technician for immediate inspection.",
    description: "An open Corrective Maintenance report with critical or major severity was found.",
    ...overrides,
  };
}

describe("AssetsAttentionPanel", () => {
  it("shows a disclosed 'data unavailable' state, not a crash or fabricated content, when summary is null", () => {
    render(<AssetsAttentionPanel summary={null} />);

    expect(screen.getByRole("heading", { name: "Assets Needing Attention" })).toBeTruthy();
    expect(screen.getByText("Data unavailable")).toBeTruthy();
  });

  it("shows an explicit empty state when summary loaded but there are no top risks", () => {
    render(<AssetsAttentionPanel summary={{ top_risks: [] }} />);

    expect(screen.getByText("No assets flagged")).toBeTruthy();
  });

  it("renders each top risk's tag, title, and action", () => {
    render(<AssetsAttentionPanel summary={{ top_risks: [topRisk()] }} />);

    expect(screen.getByText("641-P-5")).toBeTruthy();
    expect(screen.getByText("Immediate Inspection")).toBeTruthy();
    expect(screen.getByText("Dispatch a technician for immediate inspection.")).toBeTruthy();
  });

  it("renders multiple risks without collapsing or deduplicating them", () => {
    render(
      <AssetsAttentionPanel
        summary={{
          top_risks: [topRisk(), topRisk({ tag_number: "212-P-7B", rule_code: "REC_OTHER" })],
        }}
      />
    );

    expect(screen.getByText("641-P-5")).toBeTruthy();
    expect(screen.getByText("212-P-7B")).toBeTruthy();
  });
});
