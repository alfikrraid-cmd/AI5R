import { fireEvent, render, screen } from "@testing-library/react";
import ConditionMonitoringReportMeasuring from "./ConditionMonitoringReportMeasuring";

const reading = {
  id: "CM-2026-001", equipmentTag: "140-P-16B", readingDate: "2026-06-12", apiPlanSnapshot: "23/61", finding: "Mechanical seal inspected.",
  flushingTempDe: 1, flushingTempNde: 2, quenchTempDe: 3, quenchTempNde: 4,
  flushingInTempDe: 5, flushingInTempNde: 6, flushingOutTempDe: 7, flushingOutTempNde: 8,
  coolingWaterInTempDe: 9, coolingWaterInTempNde: 10, coolingWaterOutTempDe: 11, coolingWaterOutTempNde: 12,
  mechsealTempDe: 13, mechsealTempNde: 14, leakDe: true, leakNde: null,
  waterJacketTempDe: 15, waterJacketTempNde: 0, suctionTemp: null, dischargeTemp: 0, pumpOperatingState: "Running",
  stuffingBoxTempDe: 99, sealGlandTempDe: 98, verticalVibrationDe: 97, bearingTempDe: 96,
  motorCurrent: 95, quenchPressureDe: 94, suctionPressure: 93, dischargePressure: 92,
};

test("renders one selected occurrence using the actual measuring report structure", () => {
  render(<ConditionMonitoringReportMeasuring reading={reading} />);
  expect(screen.getByText("CM-2026-001")).toBeTruthy();
  expect(screen.getByText("140-P-16B")).toBeTruthy();
  expect(screen.getByText("23/61")).toBeTruthy();
  expect(screen.getByText("API Plan Recorded in Source")).toBeTruthy();
  expect(screen.getByText("Mechanical seal inspected.")).toBeTruthy();
  expect(screen.getByText("Y")).toBeTruthy();
  expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  expect(screen.getAllByText("0").length).toBeGreaterThan(0);
  expect(screen.queryByText("99")).toBeNull();
  expect(screen.queryByText("94")).toBeNull();
});

test("shows a missing snapshot as a dash without using the master API Plan", () => {
  render(<ConditionMonitoringReportMeasuring reading={{ ...reading, apiPlanSnapshot: null, apiPlan: "23/61" }} />);
  expect(screen.getByText("API Plan Recorded in Source")).toBeTruthy();
  expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  expect(screen.queryByText("23/61")).toBeNull();
});

test("closes the occurrence report", async () => {
  const onClose = vi.fn();
  render(<ConditionMonitoringReportMeasuring reading={reading} onClose={onClose} />);
  fireEvent.click(screen.getByRole("button", { name: "Close" }));
  expect(onClose).toHaveBeenCalledTimes(1);
});
