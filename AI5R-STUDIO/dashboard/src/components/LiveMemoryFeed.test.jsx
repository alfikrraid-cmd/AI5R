import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LiveMemoryFeed from "./LiveMemoryFeed";

describe("LiveMemoryFeed", () => {
  it("renders memory events in the feed", async () => {
    let instance;

    global.EventSource = vi.fn(function EventSourceMock() {
      instance = {
        close: vi.fn(),
        onmessage: null,
        onerror: null,
      };

      return instance;
    });

    render(<LiveMemoryFeed />);

    instance.onmessage({
      data: JSON.stringify({
        event_type: "MEMORY_EVENT",
        memory_id: "memory-001",
        memory_type: "EXPERIENCE",
        summary: "User completed integration sprint",
        timestamp: "2026-07-07T14:50:00Z",
      }),
    });

    await waitFor(() => {
      expect(screen.getByText("EXPERIENCE")).toBeTruthy();
      expect(screen.getByText("User completed integration sprint")).toBeTruthy();
      expect(screen.getByText("2026-07-07T14:50:00Z")).toBeTruthy();
    });
  });
});
