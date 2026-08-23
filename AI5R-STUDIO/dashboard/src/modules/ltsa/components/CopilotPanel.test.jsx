import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import CopilotPanel from "./CopilotPanel";
import { askCopilot } from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({ askCopilot: vi.fn() }));

describe("CopilotPanel", () => {
  beforeEach(() => {
    askCopilot.mockReset();
  });

  it("renders the panel with an ask control", () => {
    render(<CopilotPanel />);
    expect(screen.getByRole("heading", { name: "Engineering Copilot" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Ask" })).toBeTruthy();
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
});
