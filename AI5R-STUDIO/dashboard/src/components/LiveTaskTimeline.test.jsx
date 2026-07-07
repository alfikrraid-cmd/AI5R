import { render, screen, waitFor } from "@testing-library/react";
import { LiveStreamProvider } from "../context/LiveStreamContext";
import { describe, expect, it, vi } from "vitest";
import LiveTaskTimeline from "./LiveTaskTimeline";

describe("LiveTaskTimeline", () => {
  it("renders task events in the timeline", async () => {
    let instance;

    global.EventSource = vi.fn(function EventSourceMock() {
      instance = {
        close: vi.fn(),
        onmessage: null,
        onerror: null,
      };

      return instance;
    });

    render(<LiveStreamProvider><LiveTaskTimeline /></LiveStreamProvider>);

    instance.onmessage({
      data: JSON.stringify({
        event_type: "TASK_EVENT",
        task_id: "task-001",
        title: "Generate market insight",
        status: "RUNNING",
        timestamp: "2026-07-07T14:45:00Z",
      }),
    });

    await waitFor(() => {
      expect(screen.getByText("Generate market insight")).toBeTruthy();
      expect(screen.getByText("RUNNING")).toBeTruthy();
      expect(screen.getByText("2026-07-07T14:45:00Z")).toBeTruthy();
    });
  });
});
