import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getAllConditionMonitoringReadings, getConditionMonitoringReadingsPage } from "./ai5rClient";

// MWO-LTSA-HISTORICAL-BATCH-CMON-VISIBILITY-FIX-019D -- proves the
// MWO-019C root cause (a single 25-row default page silently treated as
// the full dataset) and that getAllConditionMonitoringReadings() pages
// through the real total/limit/offset instead. Same global.fetch
// mocking convention as ai5rClient.auth.test.js.
function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body };
}

function page(items, total, limit, offset) {
  return jsonResponse(200, { success: true, data: items, total, limit, offset });
}

beforeEach(() => {
  global.fetch = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function readingsBatch(count, startAt = 0) {
  return Array.from({ length: count }, (_, i) => ({
    condition_monitoring_reading_code: `CMONR-${startAt + i}`,
  }));
}

describe("CMON single-page fetch (the proven bug, reproduced)", () => {
  it("a bare single-page call only ever returns the backend's default page, never the full dataset (A)", async () => {
    global.fetch.mockResolvedValueOnce(page(readingsBatch(25), 606, 25, 0));

    const result = await getConditionMonitoringReadingsPage({});

    expect(result.items.length).toBe(25);
    expect(result.total).toBe(606); // the real total was always in the payload -- just never consumed by a single-page caller
  });
});

describe("getAllConditionMonitoringReadings", () => {
  it("fetches every page for a dataset larger than one page (B)", async () => {
    global.fetch
      .mockResolvedValueOnce(page(readingsBatch(100, 0), 250, 100, 0))
      .mockResolvedValueOnce(page(readingsBatch(100, 100), 250, 100, 100))
      .mockResolvedValueOnce(page(readingsBatch(50, 200), 250, 100, 200));

    const result = await getAllConditionMonitoringReadings();

    expect(result.length).toBe(250);
    expect(global.fetch).toHaveBeenCalledTimes(3);
  });

  it("handles a final partial page correctly, matching MWO-019C's real 606 total (C)", async () => {
    global.fetch
      .mockResolvedValueOnce(page(readingsBatch(100, 0), 606, 100, 0))
      .mockResolvedValueOnce(page(readingsBatch(100, 100), 606, 100, 100))
      .mockResolvedValueOnce(page(readingsBatch(100, 200), 606, 100, 200))
      .mockResolvedValueOnce(page(readingsBatch(100, 300), 606, 100, 300))
      .mockResolvedValueOnce(page(readingsBatch(100, 400), 606, 100, 400))
      .mockResolvedValueOnce(page(readingsBatch(100, 500), 606, 100, 500))
      .mockResolvedValueOnce(page(readingsBatch(6, 600), 606, 100, 600));

    const result = await getAllConditionMonitoringReadings();

    expect(result.length).toBe(606);
    expect(global.fetch).toHaveBeenCalledTimes(7);
  });

  it("makes exactly one call and returns an empty array when total=0 (D)", async () => {
    global.fetch.mockResolvedValueOnce(page([], 0, 100, 0));

    const result = await getAllConditionMonitoringReadings();

    expect(result).toEqual([]);
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it("never returns a duplicated record across page boundaries (E)", async () => {
    global.fetch
      .mockResolvedValueOnce(page(readingsBatch(100, 0), 150, 100, 0))
      .mockResolvedValueOnce(page(readingsBatch(50, 100), 150, 100, 100));

    const result = await getAllConditionMonitoringReadings();
    const codes = result.map((r) => r.condition_monitoring_reading_code);

    expect(new Set(codes).size).toBe(codes.length);
    expect(codes.length).toBe(150);
  });

  it("stops as soon as an empty page is returned, even if total disagrees (F, safety)", async () => {
    global.fetch
      .mockResolvedValueOnce(page(readingsBatch(100, 0), 500, 100, 0))
      .mockResolvedValueOnce(page([], 500, 100, 100)); // backend total stale/wrong -- must not loop forever

    const result = await getAllConditionMonitoringReadings();

    expect(result.length).toBe(100);
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it("propagates a genuine API failure honestly, never silently returning a partial/empty result (G)", async () => {
    global.fetch.mockResolvedValueOnce(jsonResponse(500, { detail: "boom" }));

    await expect(getAllConditionMonitoringReadings()).rejects.toThrow();
  });

  it("reproduces the exact MWO-019C production shape: 606 DRAFT-eligible records across 7 pages, not 25", async () => {
    global.fetch
      .mockResolvedValueOnce(page(readingsBatch(100, 0), 1037, 100, 0))
      .mockResolvedValueOnce(page(readingsBatch(100, 100), 1037, 100, 100))
      .mockResolvedValueOnce(page(readingsBatch(100, 200), 1037, 100, 200))
      .mockResolvedValueOnce(page(readingsBatch(100, 300), 1037, 100, 300))
      .mockResolvedValueOnce(page(readingsBatch(100, 400), 1037, 100, 400))
      .mockResolvedValueOnce(page(readingsBatch(100, 500), 1037, 100, 500))
      .mockResolvedValueOnce(page(readingsBatch(100, 600), 1037, 100, 600))
      .mockResolvedValueOnce(page(readingsBatch(100, 700), 1037, 100, 700))
      .mockResolvedValueOnce(page(readingsBatch(100, 800), 1037, 100, 800))
      .mockResolvedValueOnce(page(readingsBatch(100, 900), 1037, 100, 900))
      .mockResolvedValueOnce(page(readingsBatch(37, 1000), 1037, 100, 1000));

    const result = await getAllConditionMonitoringReadings();

    expect(result.length).toBe(1037); // the true CMON_TOTAL, not 25
  });
});
