/**
 * MWO-LTSA-060 -- API-to-Installation-UI field mapping, the same
 * "Raw Backend -> Mapping -> Open Design" philosophy pumpMapping.js/
 * sealMapping.js/pmMapping.js/cmMapping.js already establish.
 *
 * mapInstallationRecord() converts the real installation_report row
 * (BP-INSTALLATION/DATABASE/001_create_table.sql, snake_case columns)
 * into EXACTLY the shape InstallationOpenDesignView.jsx already expects
 * (camelCase, matching data/sampleInstallations.js's own field names
 * 1:1) -- this is the one file that changes so the existing Open Design
 * UI never has to. Every field is a real column; nothing is fabricated.
 * JSONB array columns (already deserialized to JS arrays/objects by the
 * time they reach this function) default to [] when absent, the same
 * `Array.isArray(record.checklist) ? record.checklist : []` discipline
 * pmMapping.js's own checklist field already uses -- InstallationOpenDesignView.jsx
 * calls unguarded `.map()` on several of these (siteActivities,
 * sealChamberShaftInspection, the four observation lists), so this is
 * also required for crash prevention, not just data-fidelity.
 */
// MWO-LTSA-INSTALLATION-UI-PHASE-1 -- pump_tag_number is the real FK
// column (distinct from plantEquipNo's free-text transcription of the
// report's own printed field); mapped separately so search/area-lookup
// use the canonical identity, never the free-text one.
//
// area is NOT an installation_report column -- there is none (confirmed
// against CANONICAL_SCHEMA.sql). It is resolved from the SAME canonical
// pump/asset area every other LTSA workspace already reads (pumpMapping.js's
// own `area: record.area`, sourced from GET /api/ltsa/pumps), passed in
// here as `pumpAreaByTag` (a Map<pumpTagNumber, area> built once by the
// caller from an already-fetched pump list) -- reusing the existing
// canonical area source, never a second mapping system.
//
// assemblyGpn is NOT wired to a live source. The two tables that model
// Assembly GPN (mechanical_seal_stock_pool/mechanical_seal_stock_application)
// have no client-exposed, equipment-tag-keyed lookup today, and even if
// they did, complete_seal_gpn is populated on only 2 of 226
// mechanical_seal_stock_application rows and 0 of 44 mechanical_seal_stock_pool
// rows system-wide (verified via production read-only audit) -- so wiring
// it now would show "N/A" for effectively every record regardless. Kept
// as an explicit null/N/A field rather than joined against seal_type
// (which would be inferring GPN from Seal Type, explicitly disallowed)
// so the slot exists and is correct the moment a real source appears.
export function mapInstallationRecord(record, pumpAreaByTag) {
  return {
    id: record.installation_code,

    pumpTagNumber: record.pump_tag_number ?? null,
    area: pumpAreaByTag?.get(record.pump_tag_number) ?? null,
    assemblyGpn: null,

    reportNo: record.report_no ?? null,
    tsoNo: record.tso_no ?? null,
    date: record.report_date ?? null,
    customer: record.customer ?? null,
    address: record.address ?? null,
    plant: record.plant ?? null,
    unit: record.unit ?? null,
    poNo: record.po_no ?? null,
    packingListNo: record.packing_list_no ?? null,
    location: record.location ?? null,

    equipmentMfr: record.equipment_mfr ?? null,
    modelType: record.model_type ?? null,
    size: record.size ?? null,
    configuration: record.configuration ?? null,
    serialNo: record.serial_no ?? null,
    plantEquipNo: record.plant_equip_no ?? null,
    pumpType: record.pump_type ?? null,
    shaftSpeed: record.shaft_speed ?? null,
    rotation: record.rotation ?? null,
    sealManufacture: record.seal_manufacture ?? null,
    sealType: record.seal_type ?? null,
    sealArrangement: record.seal_arrangement ?? null,
    sealSize: record.seal_size ?? null,
    materialCode: record.material_code ?? null,
    drawingNo: record.drawing_no ?? null,
    sealLocation: record.seal_location ?? null,
    sealCode: record.seal_code ?? null,

    liquid: record.liquid ?? null,
    temperatureRange: record.temperature_range ?? null,
    specificGravity: record.specific_gravity ?? null,
    viscosity: record.viscosity ?? null,
    flashPoint: record.flash_point ?? null,
    boilingPoint: record.boiling_point ?? null,
    freezePoint: record.freeze_point ?? null,
    vaporPress: record.vapor_press ?? null,
    dischargePress: record.discharge_press ?? null,
    suctionPress: record.suction_press ?? null,
    differentialPress: record.differential_press ?? null,
    stuffingBoxPress: record.stuffing_box_press ?? null,
    sealPress: record.seal_press ?? null,
    corrosionErosionBy: record.corrosion_erosion_by ?? null,
    apiPlan: record.api_plan ?? null,
    flushLiquid: record.flush_liquid ?? null,
    flushPressure: record.flush_pressure ?? null,
    flushTemp: record.flush_temp ?? null,
    flushFlowrate: record.flush_flowrate ?? null,
    bufferBarrierPress: record.buffer_barrier_press ?? null,
    bufferBarrierFluid: record.buffer_barrier_fluid ?? null,
    quenchFluid: record.quench_fluid ?? null,

    sealChamberShaftInspection: Array.isArray(record.seal_chamber_shaft_inspection)
      ? record.seal_chamber_shaft_inspection
      : [],

    basicSealCondition: record.basic_seal_condition ?? null,
    glandCondition: record.gland_condition ?? null,
    sleeveCondition: record.sleeve_condition ?? null,
    shaftCondition: record.shaft_condition ?? null,
    bearingCondition: record.bearing_condition ?? null,
    gasketCondition: record.gasket_condition ?? null,
    radialBearingNo: record.radial_bearing_no ?? null,
    thrustBearingNo: record.thrust_bearing_no ?? null,

    summaryIntro: record.summary_intro ?? null,
    siteActivityIntro: record.site_activity_intro ?? null,
    siteActivities: Array.isArray(record.site_activities) ? record.site_activities : [],

    bomCaption: record.bom_caption ?? null,
    billOfMaterial: Array.isArray(record.bill_of_material) ? record.bill_of_material : [],

    glandObservationNote: record.gland_observation_note ?? null,
    glandObservation: Array.isArray(record.gland_observation) ? record.gland_observation : [],
    sleeveObservationNote: record.sleeve_observation_note ?? null,
    sleeveObservation: Array.isArray(record.sleeve_observation) ? record.sleeve_observation : [],
    retainerDiscObservationNote: record.retainer_disc_observation_note ?? null,
    retainerDiscObservation: Array.isArray(record.retainer_disc_observation)
      ? record.retainer_disc_observation
      : [],
    cartridgeDriveCollarObservationNote: record.cartridge_drive_collar_observation_note ?? null,
    cartridgeDriveCollarObservation: Array.isArray(record.cartridge_drive_collar_observation)
      ? record.cartridge_drive_collar_observation
      : [],

    signatures: Array.isArray(record.signatures) ? record.signatures : [],

    // MWO-LTSA-068 -- previously-unmapped, already-existing NOT NULL
    // column; the "Attachments" section reuses this single real fact.
    sourceDocumentName: record.source_document_name ?? null,

    // MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 -- nullable
    // JSONB (migration 011); null stays null (honestly "no such section on
    // this report"), never defaulted to [] the way the always-present
    // observation/BOM/signature lists are -- see the column's own
    // CANONICAL_SCHEMA.sql comment.
    postInstallationReadings: Array.isArray(record.post_installation_readings)
      ? record.post_installation_readings
      : null,
  };
}

// MWO-LTSA-INSTALLATION-UI-PHASE-1 -- Phase 1 search only (Pump Tag +
// Seal Type, per this MWO's own explicit scope; not a general/advanced
// filter). Mirrors matchesDocumentSearch()'s own shape above.
export function matchesInstallationSearch(installation, term) {
  if (!term) {
    return true;
  }

  const haystack = `${installation.pumpTagNumber ?? ""} ${installation.plantEquipNo ?? ""} ${installation.sealType ?? ""}`.toLowerCase();
  return haystack.includes(term.toLowerCase());
}
