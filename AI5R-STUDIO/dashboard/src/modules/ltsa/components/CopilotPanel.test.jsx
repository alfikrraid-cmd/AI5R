import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import CopilotPanel from "./CopilotPanel";
import { askCopilot } from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({ askCopilot: vi.fn() }));

describe("CopilotPanel", () => {
  beforeEach(() => {
    askCopilot.mockReset();
  });

  it("renders the panel with title, supporting text, and an ask control", () => {
    render(<CopilotPanel />);
    expect(screen.getByRole("heading", { name: "AI Engineering Copilot" })).toBeTruthy();
    expect(
      screen.getByText("Ask about pumps, seals, maintenance, reliability, drawings, inventory, and installation history.")
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Ask" })).toBeTruthy();
  });

  it("renders all four suggested prompts", () => {
    render(<CopilotPanel />);
    expect(screen.getByRole("button", { name: "Analisa 940-P-2A" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Apa current seal 940-P-2A?" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Tampilkan maintenance history 940-P-2A" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Ada rekomendasi untuk 940-P-2A?" })).toBeTruthy();
  });

  it("clicking a suggested prompt asks that exact question, never a canned answer", async () => {
    askCopilot.mockResolvedValue({ answer: "940-P-2A is RUNNING.", kind: "FACT", evidence: [] });
    render(<CopilotPanel />);

    fireEvent.click(screen.getByRole("button", { name: "Analisa 940-P-2A" }));

    await waitFor(() => expect(askCopilot).toHaveBeenCalledWith("Analisa 940-P-2A", undefined));
    expect(await screen.findByText("940-P-2A is RUNNING.")).toBeTruthy();
  });

  it("shows a FACT answer on success", async () => {
    askCopilot.mockResolvedValue({ answer: "940-P-2A is RUNNING.", kind: "FACT", evidence: [] });
    render(<CopilotPanel />);

    fireEvent.change(screen.getByLabelText("Ask the Engineering Copilot"), { target: { value: "pump status" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByText("940-P-2A is RUNNING.")).toBeTruthy());
    expect(screen.getByText("FACT")).toBeTruthy();
  });

  it("shows a DATA_GAP answer without treating it as an error", async () => {
    askCopilot.mockResolvedValue({ answer: "No supported question was recognized.", kind: "DATA_GAP", evidence: [] });
    render(<CopilotPanel />);

    fireEvent.change(screen.getByLabelText("Ask the Engineering Copilot"), { target: { value: "weather?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByText("No supported question was recognized.")).toBeTruthy());
    expect(screen.getByText("DATA_GAP")).toBeTruthy();
  });

  it("shows an error state on transport failure", async () => {
    askCopilot.mockRejectedValue(Object.assign(new Error("Copilot API unavailable"), { status: 500 }));
    render(<CopilotPanel />);

    fireEvent.change(screen.getByLabelText("Ask the Engineering Copilot"), { target: { value: "status" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("Copilot API unavailable"));
  });

  it("shows an unauthorized state on 403", async () => {
    askCopilot.mockRejectedValue(Object.assign(new Error("Missing permission: maintenance.read"), { status: 403 }));
    render(<CopilotPanel />);

    fireEvent.change(screen.getByLabelText("Ask the Engineering Copilot"), { target: { value: "status" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("You are not authorized to use the Engineering Copilot."));
  });

  it("passes assetContext through to askCopilot unchanged", async () => {
    askCopilot.mockResolvedValue({ answer: "ok", kind: "FACT", evidence: [] });
    render(<CopilotPanel assetContext="940-P-2A" />);

    fireEvent.change(screen.getByLabelText("Ask the Engineering Copilot"), { target: { value: "seal terakhir apa?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(askCopilot).toHaveBeenCalledWith("seal terakhir apa?", "940-P-2A"));
  });

  it("displays backend-provided evidence without inventing any", async () => {
    askCopilot.mockResolvedValue({
      answer: "940-P-2A's current seal is SEAL-A-DE.",
      kind: "FACT",
      evidence: [{ source: "seal_registry", reference: "INST-043", field: "seal_code", value: "SEAL-A-DE" }],
    });
    render(<CopilotPanel />);

    fireEvent.change(screen.getByLabelText("Ask the Engineering Copilot"), { target: { value: "seal terakhir apa?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("seal_registry · INST-043 · seal_code: SEAL-A-DE")).toBeTruthy();
  });

  it("shows no evidence list when the backend returns none", async () => {
    askCopilot.mockResolvedValue({ answer: "No active recommendations.", kind: "FACT", evidence: [] });
    render(<CopilotPanel />);

    fireEvent.change(screen.getByLabelText("Ask the Engineering Copilot"), { target: { value: "recommendation?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await screen.findByText("No active recommendations.");
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("shows tools_used as a Sources line when the backend provides it", async () => {
    askCopilot.mockResolvedValue({
      answer: "Status RUNNING; seal SEAL-A-DE.",
      kind: "INTERPRETATION",
      evidence: [],
      tools_used: ["pump_status", "current_seal"],
    });
    render(<CopilotPanel />);

    fireEvent.change(screen.getByLabelText("Ask the Engineering Copilot"), { target: { value: "analisa" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Sources: Pump Status · Current Seal")).toBeTruthy();
  });

  it("omits Sources when tools_used is absent (backward-compatible response)", async () => {
    askCopilot.mockResolvedValue({ answer: "RUNNING.", kind: "FACT", evidence: [] });
    render(<CopilotPanel />);

    fireEvent.change(screen.getByLabelText("Ask the Engineering Copilot"), { target: { value: "status" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await screen.findByText("RUNNING.");
    expect(screen.queryByText(/^Sources:/)).toBeNull();
  });
});
