/**
 * MWO-LTSA-065 -- API-to-Pump-Lifecycle-UI field mapping, the same "Raw
 * Backend -> Mapping -> Open Design" convention pumpMapping.js/
 * sealMapping.js/installationMapping.js/drawingMapping.js already
 * establish. Converts GET /api/ltsa/pumps/{tag}/lifecycle's response
 * (PumpLifecycle, dataclasses.asdict()'d snake_case, MWO-LTSA-064A) into
 * one camelCase shape -- this is the one file that changes if the backend
 * DTO changes, so PumpOpenDesignView.jsx never has to.
 *
 * Every field is a real value already computed by EquipmentTimelineService.
 * build_lifecycle() -- nothing here re-derives, re-aggregates, or
 * re-resolves anything (MWO-LTSA-065's "Do not recompute lifecycle in
 * React" / "Display lifecycle values only. Do not resolve again."). Where
 * the backend record's own inner shape is itself a raw pass-through
 * (last_pm/next_pm/last_cm/last_failure -- each already an arbitrary,
 * already-real record from a different existing domain: pm_occurrence,
 * pm_schedule, cm_report, maintenance_history), this mapping keeps that
 * inner record's own field names unchanged rather than guessing a second
 * mapping for data pumpMapping.js/pmMapping.js/cmMapping.js don't own.
 */
export function mapPumpLifecycleRecord(payload) {
  const data = payload?.data ?? {};

  return {
    tagNumber: data.tag_number ?? null,
    pump: data.pump ?? null,
    currentState: mapCurrentState(data.current_state),
    timeline: (data.timeline ?? []).map(mapTimelineEvent),
    analytics: mapAnalytics(data.analytics),
    relatedEngineering: mapRelatedEngineering(data.related_engineering),
  };
}

function mapCurrentState(currentState) {
  if (!currentState) {
    return {
      currentInstallation: null,
      currentSeal: null,
      elapsedServiceDays: null,
      runningHoursDerived: null,
      lastPm: null,
      nextPm: null,
      lastCm: null,
      lastFailure: null,
      openWorkOrders: [],
    };
  }

  return {
    currentInstallation: mapCurrentInstallation(currentState.current_installation),
    currentSeal: mapCurrentSeal(currentState.current_seal),
    elapsedServiceDays: currentState.elapsed_service_days ?? null,
    runningHoursDerived: currentState.running_hours_derived ?? null,
    lastPm: currentState.last_pm ?? null,
    nextPm: currentState.next_pm ?? null,
    lastCm: currentState.last_cm ?? null,
    lastFailure: currentState.last_failure ?? null,
    openWorkOrders: currentState.open_work_orders ?? [],
  };
}

function mapCurrentInstallation(record) {
  if (!record) {
    return null;
  }

  return {
    installationCode: record.installation_code ?? null,
    reportNo: record.report_no ?? null,
    reportDate: record.report_date ?? null,
    plantEquipNo: record.plant_equip_no ?? null,
    sealCode: record.seal_code ?? null,
    sealType: record.seal_type ?? null,
    sealManufacture: record.seal_manufacture ?? null,
    drawingNo: record.drawing_no ?? null,
    sourceDocumentName: record.source_document_name ?? null,
  };
}

function mapCurrentSeal(record) {
  if (!record) {
    return null;
  }

  return {
    sealCode: record.seal_code ?? null,
    sealName: record.seal_name ?? null,
    manufacturer: record.manufacturer ?? null,
    model: record.model ?? null,
    shaftSize: record.shaft_size ?? null,
    material: record.material ?? null,
    temperatureLimit: record.temperature_limit ?? null,
    pressureLimit: record.pressure_limit ?? null,
    status: record.status ?? null,
    installationCode: record.installation_code ?? null,
    installedAt: record.installed_at ?? null,
    source: record.source ?? null,
  };
}

function mapTimelineEvent(event) {
  return {
    id: event.id ?? null,
    eventType: event.event_type ?? null,
    occurredAt: event.occurred_at ?? null,
    title: event.title ?? null,
    description: event.description ?? null,
    severity: event.severity ?? null,
    source: event.source ?? null,
    derived: event.derived ?? null,
    payload: event.payload ?? null,
  };
}

function mapAnalytics(analytics) {
  if (!analytics) {
    return {
      elapsedServiceDays: null,
      pmCount: null,
      cmCount: null,
      failureCount: null,
      mtbf: null,
      mtbr: null,
      averageSealLife: null,
      healthIndex: null,
      availability: null,
      reliability: null,
    };
  }

  return {
    elapsedServiceDays: analytics.elapsed_service_days ?? null,
    pmCount: analytics.pm_count ?? null,
    cmCount: analytics.cm_count ?? null,
    failureCount: analytics.failure_count ?? null,
    mtbf: analytics.mtbf ?? null,
    mtbr: analytics.mtbr ?? null,
    averageSealLife: analytics.average_seal_life ?? null,
    healthIndex: analytics.health_index ?? null,
    availability: analytics.availability ?? null,
    reliability: analytics.reliability ?? null,
  };
}

function mapRelatedEngineering(relatedEngineering) {
  if (!relatedEngineering) {
    return {
      pmSchedules: [],
      cmReports: [],
      workOrders: [],
      breakdownHistory: [],
      drawings: [],
      documents: [],
      inventory: [],
    };
  }

  return {
    pmSchedules: relatedEngineering.pm_schedules ?? [],
    cmReports: relatedEngineering.cm_reports ?? [],
    workOrders: relatedEngineering.work_orders ?? [],
    breakdownHistory: relatedEngineering.breakdown_history ?? [],
    drawings: relatedEngineering.drawings ?? [],
    documents: relatedEngineering.documents ?? [],
    inventory: relatedEngineering.inventory ?? [],
  };
}
