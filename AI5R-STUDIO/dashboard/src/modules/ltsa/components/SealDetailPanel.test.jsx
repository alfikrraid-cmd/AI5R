import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SealDetailPanel from "./SealDetailPanel";

const SEAL = {
  code: "SC-003",
  name: "Flowserve ISC2",
  type: "Dual Cartridge Seal",
  manufacturer: "Flowserve",
  compatiblePumps: ["PMP-003"],
  compatibleSeals: ["SC-004"],
  status: "ACTIVE",
  recommendation: "Recommended: purchase additional stock.",
  knowledgeLinks: ["Seal Stock Report Q1"],
};

describe("SealDetailPanel", () => {
  it("renders an empty state when no seal is selected", () => {
    render(<SealDetailPanel seal={null} />);

    expect(screen.getByText(/select a seal/i)).toBeTruthy();
  });

  it("renders every required field for a selected seal", () => {
    render(<SealDetailPanel seal={SEAL} />);

    expect(screen.getByText("Flowserve ISC2")).toBeTruthy();
    expect(screen.getByText("SC-003")).toBeTruthy();
    expect(screen.getByText("Dual Cartridge Seal")).toBeTruthy();
    expect(screen.getByText("Flowserve")).toBeTruthy();
    expect(screen.getByText("ACTIVE")).toBeTruthy();
    expect(screen.getByText(SEAL.recommendation)).toBeTruthy();
  });

  it("renders compatible pumps and compatible seals as badges", () => {
    render(<SealDetailPanel seal={SEAL} />);

    expect(screen.getByText("PMP-003")).toBeTruthy();
    expect(screen.getByText("SC-004")).toBeTruthy();
  });

  it("renders every knowledge link as a badge", () => {
    render(<SealDetailPanel seal={SEAL} />);

    expect(screen.getByText("Seal Stock Report Q1")).toBeTruthy();
  });

  it("renders fallback text when compatible pumps/seals/knowledge links are empty", () => {
    render(
      <SealDetailPanel
        seal={{ ...SEAL, compatiblePumps: [], compatibleSeals: [], knowledgeLinks: [] }}
      />
    );

    expect(screen.getByText(/no compatible pumps/i)).toBeTruthy();
    expect(screen.getByText(/no compatible seals/i)).toBeTruthy();
    expect(screen.getByText(/no knowledge links/i)).toBeTruthy();
  });
});
