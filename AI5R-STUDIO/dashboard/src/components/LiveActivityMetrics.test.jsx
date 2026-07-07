import { render, screen, waitFor } from "@testing-library/react";
import { LiveStreamProvider } from "../context/LiveStreamContext";
import { describe, expect, it, vi } from "vitest";
import LiveActivityMetrics from "./LiveActivityMetrics";

describe("LiveActivityMetrics", () => {
  it("updates metrics from runtime events", async () => {
    let instance;

    global.EventSource = vi.fn(function EventSourceMock() {
      instance = {
        close: vi.fn(),
        onmessage: null,
        onerror: null,
      };

      return instance;
    });

    render(<LiveStreamProvider><LiveActivityMetrics /></LiveStreamProvider>);

    instance.onmessage({
      data: JSON.stringify({
        event_type: "TASK_EVENT",
      }),
    });

    instance.onmessage({
      data: JSON.stringify({
        event_type: "MEMORY_EVENT",
      }),
    });

    instance.onmessage({
      data: JSON.stringify({
        event_type: "REASONING_EVENT",
      }),
    });

    instance.onmessage({
      data: JSON.stringify({
        event_type: "ORGANIZATION_SNAPSHOT",
        workers: [{}, {}, {}],
      }),
    });

    await waitFor(() => {
      expect(screen.getByText("4")).toBeTruthy();
      expect(screen.getByText("3")).toBeTruthy();
    });
  });
});
