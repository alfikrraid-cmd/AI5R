import { fireEvent, render, screen, within } from "@testing-library/react";
import { ConditionMonitoringHistory } from "./KnowledgeWorkspace";

const oldReading = {
  id: "CMONR-OLD", readingDate: "2026-06-05", apiPlanSnapshot: "23/61", pumpOperatingState: "Standby",
  mechsealTempDe: 31, mechsealTempNde: null, leakDe: true, leakNde: null,
  flushingTempDe: 30, flushingTempNde: null, workflowStatus: "FINALIZED", finding: "Old occurrence finding",
};

const newReading = {
  id: "CMONR-NEW", readingDate: "2026-06-12", apiPlanSnapshot: "32/61", pumpOperatingState: "Running",
  mechsealTempDe: 62, mechsealTempNde: 74, leakDe: false, leakNde: false,
  flushingTempDe: 92, flushingTempNde: 82, workflowStatus: "SUBMITTED", finding: "New occurrence finding",
};

test("renders every actual occurrence and preserves occurrence-specific values", () => {
  render(<ConditionMonitoringHistory readings={[oldReading, newReading]} />);

  const oldRow = screen.getByTestId("cm-history-CMONR-OLD");
  expect(oldRow.textContent).toContain("2026-06-05");
  expect(oldRow.textContent).not.toContain("23/61");
  expect(oldRow.textContent).toContain("Standby");
  expect(oldRow.textContent).toContain("DE Y / NDE —");
  expect(oldRow.textContent).toContain("DE 31 / NDE —");
  expect(oldRow.textContent).toContain("Old occurrence finding");

  const newRow = screen.getByTestId("cm-history-CMONR-NEW");
  expect(newRow.textContent).toContain("2026-06-12");
  expect(newRow.textContent).not.toContain("32/61");
  expect(newRow.textContent).toContain("Running");
  expect(newRow.textContent).toContain("DE N / NDE N");
  expect(newRow.textContent).toContain("DE 62 / NDE 74");
  expect(newRow.textContent).toContain("New occurrence finding");
});

test("shows the required empty state only for zero actual occurrences", () => {
  render(<ConditionMonitoringHistory readings={[]} />);
  expect(screen.getByText("Belum ada riwayat CM")).toBeTruthy();
});

test("opens Report Measuring for the selected occurrence without substituting another row", () => {
  render(<ConditionMonitoringHistory readings={[oldReading, newReading]} />);

  fireEvent.click(screen.getAllByRole("button", { name: "View Report Measuring" })[0]);
  const report = screen.getByTestId("report-measuring");
  expect(within(report).getByText("CMONR-OLD")).toBeTruthy();
  expect(within(report).getByText("23/61")).toBeTruthy();
  expect(within(report).queryByText("CMONR-NEW")).toBeNull();

  fireEvent.click(screen.getByRole("button", { name: "Close" }));
  fireEvent.click(screen.getAllByRole("button", { name: "View Report Measuring" })[1]);
  const newReport = screen.getByTestId("report-measuring");
  expect(within(newReport).getByText("CMONR-NEW")).toBeTruthy();
  expect(within(newReport).getByText("32/61")).toBeTruthy();
  expect(within(newReport).queryByText("CMONR-OLD")).toBeNull();
});
