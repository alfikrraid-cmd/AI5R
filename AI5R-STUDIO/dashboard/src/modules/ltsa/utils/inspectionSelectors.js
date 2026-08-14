export function inspectionSummary(inspections) {
  return {
    total: inspections.length,
    findings: inspections.reduce(
      (total, inspection) => total + Number(inspection.finding_count ?? 0),
      0
    ),
    latestDate: inspections[0]?.inspection_date ?? null,
  };
}

export function inspectionStatusVariant(status) {
  const normalized = String(status ?? "").trim().toLowerCase();

  if (["closed", "approved", "passed", "complete"].includes(normalized)) {
    return "success";
  }

  if (["open", "attention", "in progress"].includes(normalized)) {
    return "warning";
  }

  if (["failed", "rejected", "critical"].includes(normalized)) {
    return "danger";
  }

  return "info";
}
