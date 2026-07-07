import { render, screen, waitFor } from "@testing-library/react";
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

    render(<LiveActivityMetrics />);

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
        workers: [{ id: 1 }, { id: 2 }, { id: 3 }],
      }),
    });

    await waitFor(() => {
      expect(screen.getByText("4")).toBeTruthy();
      expect(screen.getByText("3")).toBeTruthy();
    });
  });
});
