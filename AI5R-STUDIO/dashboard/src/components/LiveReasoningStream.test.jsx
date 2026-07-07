import { render, screen, waitFor } from "@testing-library/react";
import { LiveStreamProvider } from "../context/LiveStreamContext";
import { describe, expect, it, vi } from "vitest";
import LiveReasoningStream from "./LiveReasoningStream";

describe("LiveReasoningStream", () => {
  it("renders reasoning events", async () => {
    let instance;

    global.EventSource = vi.fn(function EventSourceMock() {
      instance = {
        close: vi.fn(),
        onmessage: null,
        onerror: null,
      };
      return instance;
    });

    render(<LiveStreamProvider><LiveReasoningStream /></LiveStreamProvider>);

    instance.onmessage({
      data: JSON.stringify({
        event_type: "REASONING_EVENT",
        stage: "PLANNING",
        summary: "Generating execution plan",
        timestamp: "2026-07-07T15:00:00Z",
      }),
    });

    await waitFor(() => {
      expect(screen.getByText("PLANNING")).toBeTruthy();
      expect(screen.getByText("Generating execution plan")).toBeTruthy();
    });
  });
});
