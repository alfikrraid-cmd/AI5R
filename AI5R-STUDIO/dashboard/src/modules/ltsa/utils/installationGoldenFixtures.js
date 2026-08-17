/**
 * MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 -- SYNTHETIC
 * structural fixtures, TEST-ONLY (not production sample data, unlike
 * data/sampleInstallations.js's one real, literal transcription).
 *
 * Per this MWO's own Phase 9 ("Create synthetic test fixtures
 * STRUCTURALLY derived from the five reports... Do NOT commit confidential
 * report PDFs"), these four fixtures reproduce the STRUCTURAL pattern
 * MWO-LTSA-INSTALLATION-GOLDEN-SAMPLE-VALIDATION-001 found in golden
 * samples SCAN 002-005 (report content, customer addresses, pressures,
 * and other business values are synthetic placeholders, not the real
 * report's own numbers) -- every shape (SPARE-suffixed tag, triple-seal
 * compound values, dual-position DE/NDE, multi-date activity grouping,
 * post-installation readings, free-text BOM disposition) is real and
 * evidenced, only the specific values are not.
 *
 * 211-P-14B's pattern (single-position, single-day, simple BOM) is
 * already covered by data/sampleInstallations.js's own real record, so it
 * is not duplicated here.
 */

// 212-P-25A-SPARE-style: SPARE literal identity, triple seal (compound
// seal_type/seal_size), rich/long BOM (7 columns instead of 4).
export const sparePatternFixture = {
  id: "INSTL-FIXTURE-SPARE",
  reportNo: "SYN/INSTL/TAP/00-0000",
  tsoNo: null,
  date: "March 01, 2026",
  customer: "Synthetic Test Customer",
  address: "Synthetic Address, Test City",
  plant: "TESTPLANT",
  unit: "TestUnit",
  poNo: "9999999999",
  packingListNo: null,
  location: "Workshop",

  equipmentMfr: "Synthetic Mfr",
  modelType: "SYN-000",
  size: "00/000SCSS",
  configuration: null,
  serialNo: "SYN-000000",
  // SPARE is part of the printed tag itself, verbatim -- never split into
  // a separate identity concept, and never stripped before pump matching.
  plantEquipNo: "999-P-99Z SPARE",
  pumpType: "OH6",
  shaftSpeed: "14000 rpm",
  rotation: null,
  sealManufacture: "John Crane",
  // Triple seal: three positions compounded into one slash-delimited
  // string, matching the source report's own printed representation
  // exactly -- not split into 3 columns, since the source itself never
  // splits them either.
  sealType: "8AB/8AB/8AB Triple Seal",
  sealArrangement: "Triple Seal",
  sealSize: '1.250"/1.500"/1.500"',
  materialCode: null,
  drawingNo: "SYN-000000-1",
  sealLocation: null,
  sealCode: null,

  liquid: "Synthetic Overhead Stream",
  temperatureRange: "38°C",
  specificGravity: "0.559",
  viscosity: "0.16 cP",
  flashPoint: null,
  boilingPoint: null,
  freezePoint: null,
  vaporPress: "5.25 kg/cm²g",
  dischargePress: "34.32 kg/cm²g",
  suctionPress: "4.48-6.3 kg/cm²g",
  differentialPress: null,
  stuffingBoxPress: null,
  sealPress: "7.85 kg/cm²g",
  corrosionErosionBy: null,
  apiPlan: "13/52",
  flushLiquid: null,
  flushPressure: null,
  flushTemp: null,
  flushFlowrate: null,
  bufferBarrierPress: null,
  bufferBarrierFluid: "Lube Oil",
  quenchFluid: null,

  // A "SPARE" assembly is pre-built, not installed in-situ -- no shaft/
  // chamber measurements were taken, matching the real report exactly.
  sealChamberShaftInspection: [
    { item: "Shaft Run Out", value: null, standard: "Standard 0.050 – 0.076 mm" },
    { item: "Shaft End Play/Axial Float", value: null, standard: "Standard 0.025 – 0.127 mm" },
    { item: "Radial Bearing Fit", value: null, standard: "Standard 0.050 – 0.076 mm" },
    { item: "Squareness/Seal Chamber Face Run Out", value: null, standard: "Limits refer to seal manual" },
    { item: "Seal Chamber Concentricity Run Out", value: null, standard: "Limits refer to seal manual" },
  ],

  basicSealCondition: "New",
  glandCondition: "New",
  sleeveCondition: "New",
  shaftCondition: "Old",
  bearingCondition: "New",
  gasketCondition: "New",
  radialBearingNo: null,
  thrustBearingNo: null,

  summaryIntro: "Synthetic Test Customer invited the service provider to assist in building a spare seal assembly.",
  siteActivityIntro: "Site activity carried out on March 01, 2026 with following detail:",
  siteActivities: [
    {
      date: "March 01, 2026",
      activities: ["Work permit.", "Assembly of mechanical seal parts.", "Hydrostatic testing on pumps."],
    },
  ],

  bomCaption: "Mechanical Seal Assembly SYN-000000-1 Type Triple Seal (99999999)",
  // Richer, 7-column BOM shape -- drawingNumber/materialCode/description/
  // material distinct fields, not squeezed into a single partName.
  billOfMaterial: [
    { item: 1, drawingNumber: "F 0000 000", materialCode: "0000", description: "Mating Ring", material: "Tungsten Carbide", qty: 1, workRequired: "Replace" },
    { item: 2, drawingNumber: "A0 0000 000", materialCode: "0000", description: "Primary Ring", material: "Carbon", qty: 1, workRequired: "Replace" },
    { item: 3, drawingNumber: "0000 000", materialCode: "0000", description: "O-Ring", material: "Fluoroelastomer", qty: 3, workRequired: "Replace" },
  ],

  glandObservationNote: "Fill following observation list if gland is reused.",
  glandObservation: [
    { item: "Inboard Side / Outboard Side re-used", checked: false },
    { item: "Corrosion", checked: false },
  ],
  sleeveObservationNote: "Fill following observation list if sleeve is reused.",
  sleeveObservation: [{ item: "Inboard Side / Outboard Side re-used", checked: false }],
  retainerDiscObservationNote: "Fill following observation list if retainer / disc is reused.",
  retainerDiscObservation: [{ item: "Inboard Side / Outboard Side re-used", checked: false }],
  cartridgeDriveCollarObservationNote: "Fill following observation list if drive collar is reused.",
  cartridgeDriveCollarObservation: [{ item: "Distortion", checked: false }],

  signatures: [
    { id: 1, company: "Synthetic Service Co", name: "Synthetic Technician", title: "Service", date: "01-03-2026" },
    { id: 2, company: "Synthetic Service Co", name: "Synthetic Engineer", title: "Service Engineer", date: "01-03-2026" },
    { id: 3, company: "Synthetic Customer Co", name: null, title: "Technician II RE", date: "01-03-2026" },
    { id: 4, company: "Synthetic Customer Co", name: "Synthetic Inspector", title: "Jr. Eng I RE Insp", date: "18-02-2026" },
  ],

  sourceDocumentName: "SYNTHETIC FIXTURE 212-P-25A SPARE PATTERN.pdf",
  postInstallationReadings: null,
};

// 211-P-2A-DE-style: DE-only, multi-day (2 date groups), post-installation
// readings present (single-position DE, no NDE column).
export const deOnlyMultiDayReadingsFixture = {
  id: "INSTL-FIXTURE-DE-ONLY",
  reportNo: "SYN/INSTL/TAP/00-0001",
  tsoNo: null,
  date: "March 03, 2026",
  customer: "Synthetic Test Customer",
  address: "Synthetic Address, Test City",
  plant: "TESTPLANT",
  unit: "TestReactor",
  poNo: "9999999998",
  packingListNo: null,
  location: "TestReactor MA-2 TESTPLANT",

  equipmentMfr: "Synthetic Pump Co",
  modelType: "SYN 4x11 Stg",
  size: null,
  configuration: null,
  serialNo: null,
  plantEquipNo: "999-P-2A (DE)",
  pumpType: "BB",
  shaftSpeed: "5000 rpm",
  rotation: "CW",
  sealManufacture: "John Crane",
  sealType: "T8B1-RS",
  sealArrangement: "Cartridge",
  sealSize: '4.1/2"',
  materialCode: "AR1S1/P",
  drawingNo: "SYN-8B-0001",
  sealLocation: "DE",
  sealCode: null,

  liquid: "Synthetic Recycle Stream",
  temperatureRange: "221°C",
  specificGravity: "0.724",
  viscosity: "0.96 cP",
  flashPoint: null,
  boilingPoint: null,
  freezePoint: null,
  vaporPress: "0.11 kg/cm²g",
  dischargePress: "200.04 kg/cm²g",
  suctionPress: "3.21-5.24 kg/cm²g",
  differentialPress: null,
  stuffingBoxPress: "4 kg/cm²g",
  sealPress: "200.04 kg/cm²g",
  corrosionErosionBy: null,
  apiPlan: "22/62",
  flushLiquid: "Water",
  flushPressure: "4 kg/cm²g",
  flushTemp: "150°C",
  flushFlowrate: "14 l/m",
  bufferBarrierPress: null,
  bufferBarrierFluid: null,
  quenchFluid: "Steam",

  sealChamberShaftInspection: [
    { item: "Shaft Run Out", value: null, standard: "Standard 0.050 – 0.076 mm" },
    { item: "Shaft End Play/Axial Float", value: null, standard: "Standard 0.025 – 0.127 mm" },
    { item: "Radial Bearing Fit", value: null, standard: "Standard 0.050 – 0.076 mm" },
    { item: "Squareness/Seal Chamber Face Run Out", value: null, standard: "Limits refer to seal manual" },
    { item: "Seal Chamber Concentricity Run Out", value: null, standard: "Limits refer to seal manual" },
  ],

  basicSealCondition: "New",
  glandCondition: "Old",
  sleeveCondition: "New",
  shaftCondition: "Old",
  bearingCondition: "Old",
  gasketCondition: "New",
  radialBearingNo: null,
  thrustBearingNo: null,

  summaryIntro: "Synthetic Test Customer invited the service provider to assist in replacing the seal on a test pump.",
  siteActivityIntro: "Field activities were carried out on March 03-04, 2026 and March 08, 2026 with the following details:",
  // Multi-day: two independent date groups, chronology preserved.
  siteActivities: [
    {
      date: "Tuesday-Wednesday, March 03-04, 2026",
      activities: [
        "Work permit.",
        "Dismantling the gland plate from the pump stuffing box.",
        "Assembly of mechanical seal parts.",
        "Check the pump rotation.",
      ],
    },
    {
      date: "Sunday, March 08, 2026",
      activities: ["Work permit.", "Monitoring pump Tag No. 999-P-2A"],
    },
  ],

  bomCaption: "Mechanical Seal Assembly SYN-8B-0001 Issue C Type-8B1RS Size 4.1/2\" (00000000)",
  billOfMaterial: [
    { item: 1, drawingNumber: "0000-000-000", materialCode: "9205", description: "Seat/Mating Ring", material: "Tungsten Carbide", qty: 1, workRequired: "Replace" },
    { item: 2, drawingNumber: "0000-000-000", materialCode: "9579", description: "O-Ring", material: "FFKM", qty: 1, workRequired: "Replace" },
    { item: 3, drawingNumber: "By Mfr", materialCode: null, description: "Drive Collar", material: "304 S.S.", qty: 1, workRequired: "Clean, reuse" },
  ],

  glandObservationNote: "Fill following observation list if gland is reused.",
  glandObservation: [
    { item: "Inboard Side / Outboard Side re-used", checked: true },
    { item: "Contact with Sleeve", checked: true },
    { item: "Corrosion", checked: false },
  ],
  sleeveObservationNote: "Fill following observation list if sleeve is reused.",
  sleeveObservation: [{ item: "Inboard Side / Outboard Side re-used", checked: false }],
  retainerDiscObservationNote: "Fill following observation list if retainer / disc is reused.",
  retainerDiscObservation: [{ item: "Inboard Side / Outboard Side re-used", checked: false }],
  cartridgeDriveCollarObservationNote: "Fill following observation list if drive collar is reused.",
  cartridgeDriveCollarObservation: [{ item: "Distortion", checked: false }],

  signatures: [
    { id: 1, company: "Synthetic Service Co", name: "Synthetic Technician", title: "Service", date: "08-03-2026" },
    { id: 2, company: "Synthetic Service Co", name: "Synthetic Engineer", title: "Service Engineer", date: "08-03-2026" },
    { id: 3, company: "Synthetic Customer Co", name: null, title: "Sr. Tech. 2 RE", date: "13-03-2026" },
    { id: 4, company: "Synthetic Customer Co", name: "Synthetic Inspector", title: "Jr. Eng I RE Insp", date: "18-03-2026" },
  ],

  sourceDocumentName: "SYNTHETIC FIXTURE 211-P-2A DE PATTERN.pdf",
  // DE-only report: post-installation readings carry no `nde` key at all
  // (single-position), matching the real report's own DE-only column set.
  postInstallationReadings: [
    { measurement: "Pump Condition", value: "Running", dateTime: "2026-03-08T10:15:00" },
    { measurement: "Suction Temperature", value: "167", unit: "°C", dateTime: "2026-03-08T10:15:00" },
    { measurement: "Mechanical Seal Gland Temperature", de: "107", unit: "°C", dateTime: "2026-03-08T10:15:00" },
    { measurement: "Connection Condition", de: "v", dateTime: "2026-03-08T10:15:00" },
    { measurement: "Mechanical Seal Condition", value: "No Leak", dateTime: "2026-03-08T10:15:00" },
  ],
};

// 212-P-13AR-style: DE/NDE dual position, three date groups, dual-position
// observations, post-installation readings with both DE and NDE columns.
export const dualPositionThreeDateGroupsFixture = {
  id: "INSTL-FIXTURE-DE-NDE",
  reportNo: "SYN/INSTL/TAP/00-0002",
  tsoNo: null,
  date: "March 10, 2026",
  customer: "Synthetic Refinery Co",
  address: "Synthetic Address, Test City",
  plant: "TESTPLANT",
  unit: "TestUnit",
  poNo: null,
  packingListNo: null,
  location: "TestUnit MA-2 dan Workshop TESTPLANT",

  equipmentMfr: "Synthetic Pump Co",
  modelType: "SYN 6x17A BB2",
  size: null,
  configuration: null,
  serialNo: null,
  plantEquipNo: "999-P-13AR",
  pumpType: "BB",
  shaftSpeed: "2980 rpm",
  rotation: "CCW",
  sealManufacture: "John Crane",
  sealType: "T1604DP",
  sealArrangement: "Cartridge",
  sealSize: "60 MM",
  materialCode: null,
  drawingNo: "SYN/00000",
  // Compound DE,NDE seal_location -- dual position confirmed at the header
  // level; the observation checklists below carry the matching dual state.
  sealLocation: "DE, NDE",
  sealCode: null,

  liquid: "Synthetic Bottoms Stream",
  temperatureRange: "352°C",
  specificGravity: "610 kg/m³",
  viscosity: "0.56 cP",
  flashPoint: null,
  boilingPoint: null,
  freezePoint: null,
  vaporPress: "0.11 kg/cm²g",
  dischargePress: "12.25/14.34 kg/cm²g",
  suctionPress: "1.80/3.89 kg/cm²g",
  differentialPress: null,
  stuffingBoxPress: "4 kg/cm²g",
  sealPress: "1.80/3.89 kg/cm²g",
  corrosionErosionBy: null,
  apiPlan: "32/62",
  flushLiquid: null,
  flushPressure: null,
  flushTemp: null,
  flushFlowrate: null,
  bufferBarrierPress: null,
  bufferBarrierFluid: null,
  quenchFluid: "Steam",

  sealChamberShaftInspection: [
    { item: "Shaft Run Out", value: null, standard: "Standard 0.050 – 0.076 mm" },
    { item: "Shaft End Play/Axial Float", value: "0.07 mm", standard: "Standard 0.025 – 0.127 mm" },
    { item: "Radial Bearing Fit", value: null, standard: "Standard 0.050 – 0.076 mm" },
    { item: "Squareness/Seal Chamber Face Run Out", value: null, standard: "Limits refer to seal manual" },
    { item: "Seal Chamber Concentricity Run Out", value: null, standard: "Limits refer to seal manual" },
  ],

  basicSealCondition: "New",
  glandCondition: "Old",
  sleeveCondition: "Old",
  shaftCondition: "Old",
  bearingCondition: "New",
  gasketCondition: "New",
  radialBearingNo: null,
  thrustBearingNo: null,

  summaryIntro: "Synthetic Refinery Co invited the service provider to assist in replacing the seal on a test pump.",
  siteActivityIntro: "Field activities were carried out on March 10-12, 2026, and March 18, 2026 with the following details:",
  // Three date groups -- the richest chronology among the golden samples.
  siteActivities: [
    { date: "Sunday-Monday, March 10-11, 2026", activities: ["Work permit.", "Open the set screw and then close the setting washer/spacer on the cover/gland plate."] },
    { date: "Tuesday-Wednesday, March 12-13, 2026", activities: ["Work permit.", "Shaft end play measurement.", "Hydrostatic testing on pumps."] },
    { date: "Tuesday, March 18, 2026", activities: ["Work permit.", "Monitoring pump Tag No. 999-P-13AR."] },
  ],

  bomCaption: "Mechanical Seal Assembly SYN/00000 Issue E Type-1604DP Size 60 MM (00000000)",
  // DE/NDE-split disposition: two flat columns (workRequiredDE/
  // workRequiredNDE), never a nested value -- a nested object would both
  // be unrenderable as a plain table cell and would hide the two
  // independent dispositions behind an opaque structure.
  billOfMaterial: [
    { item: 1, drawingNumber: "S000000-00", description: "Seal Head Assy", material: "Inc.600, 718/UNS-N07718", qty: 1, workRequiredDE: "Replace", workRequiredNDE: "Replace" },
    { item: 2, drawingNumber: "0000/000/000", description: "Skt Head Screw", material: "Stainless Steel / 316", qty: 4, workRequiredDE: "Replace", workRequiredNDE: "Replace" },
    { item: 8, drawingNumber: "D/00000/0/000", description: "Mating Ring Adapter", material: "Stainless Steel / 316", qty: 1, workRequiredDE: "Clean, reuse", workRequiredNDE: "Clean, reuse" },
  ],

  glandObservationNote: "Fill following observation list if gland is reused.",
  // Dual-position (DE/NDE) observation shape -- checkedDE/checkedNDE
  // instead of a single checked boolean, never collapsed into one value.
  glandObservation: [
    { item: "Inboard Side / Outboard Side re-used", checkedDE: true, checkedNDE: true },
    { item: "Corrosion", checkedDE: false, checkedNDE: false },
    { item: "Contact with Sleeve", checkedDE: true, checkedNDE: true },
  ],
  sleeveObservationNote: "Fill following observation list if sleeve is reused.",
  sleeveObservation: [
    { item: "Inboard Side / Outboard Side re-used", checkedDE: true, checkedNDE: true },
    { item: "Contact with Gland", checkedDE: true, checkedNDE: true },
    { item: "Fretting", checkedDE: false, checkedNDE: false },
  ],
  retainerDiscObservationNote: "Fill following observation list if retainer / disc is reused.",
  retainerDiscObservation: [{ item: "Inboard Side / Outboard Side re-used", checkedDE: false, checkedNDE: false }],
  cartridgeDriveCollarObservationNote: "Fill following observation list if drive collar is reused.",
  cartridgeDriveCollarObservation: [{ item: "Inboard Side / Outboard Side re-used", checkedDE: true, checkedNDE: true }],

  signatures: [
    { id: 1, company: "Synthetic Service Co", name: "Synthetic Technician", title: "Service", date: "18-03-2026" },
    { id: 2, company: "Synthetic Service Co", name: "Synthetic Engineer", title: "Service Eng.", date: "18-03-2026" },
    { id: 3, company: "Synthetic Customer Co", name: "Synthetic Reviewer", title: "Technician II RE", date: "18-03-2026" },
    { id: 4, company: "Synthetic Customer Co", name: "Synthetic Inspector", title: "Jr. Eng I RE Insp", date: "18-03-2026" },
  ],

  sourceDocumentName: "SYNTHETIC FIXTURE 212-P-13AR PATTERN.pdf",
  // Dual-position post-installation readings: both `de` and `nde` present
  // per measurement, never collapsed into one shared value.
  postInstallationReadings: [
    { measurement: "Pump Condition", value: "Running", dateTime: "2026-03-18T10:15:00" },
    { measurement: "Suction Temperature", value: "352", unit: "°C", dateTime: "2026-03-18T10:15:00" },
    { measurement: "Mechanical Seal Gland Temperature", de: "180", nde: "190", unit: "°C", dateTime: "2026-03-18T10:15:00" },
    { measurement: "Flushing Temperature", de: "170", nde: "140", unit: "°C", dateTime: "2026-03-18T10:15:00" },
    { measurement: "Connection Condition", de: "v", nde: "v", dateTime: "2026-03-18T10:15:00" },
    { measurement: "Mechanical Seal Condition", de: "No Leak", nde: "No Leak", dateTime: "2026-03-18T10:15:00" },
  ],
};

// 702-P-2-style: free-text BOM disposition beyond Replace/Clean-reuse,
// fully populated shaft/seal-chamber inspection.
export const freeTextDispositionFixture = {
  id: "INSTL-FIXTURE-FREE-TEXT-DISPOSITION",
  reportNo: "SYN/INSTL/TAP/00-0003",
  tsoNo: null,
  date: "March 15, 2026",
  customer: "Synthetic Refinery Co",
  address: "Synthetic Address, Test City",
  plant: "TESTPLANT",
  unit: "TestH2Plant",
  poNo: "SP No : 0000000000/SP/TST/2026-S0",
  packingListNo: "000/SYN/TST/0/2026",
  location: "Workshop TEST",

  equipmentMfr: "Synthetic Pump Co",
  modelType: "SYN-32/250",
  size: "32-250",
  configuration: null,
  serialNo: "SYN000.000",
  plantEquipNo: "999-P-2",
  pumpType: "OH2",
  shaftSpeed: "2950 rpm",
  rotation: "CW",
  sealManufacture: "John Crane",
  sealType: "T48MP",
  sealArrangement: "Non-Cartridge Single Seal",
  sealSize: '1.7/8"',
  materialCode: "AR1K1/P",
  drawingNo: "SYN13435",
  sealLocation: "DE",
  sealCode: null,

  liquid: "Synthetic Condensate",
  temperatureRange: "124°C",
  specificGravity: "0.941",
  viscosity: "0.24 cP",
  flashPoint: null,
  boilingPoint: null,
  freezePoint: null,
  vaporPress: null,
  dischargePress: "23.1 kg/cm²g",
  suctionPress: "15.96-20 kg/cm²g",
  differentialPress: null,
  stuffingBoxPress: null,
  sealPress: "7.14 kg/cm²g",
  corrosionErosionBy: null,
  apiPlan: "12/61",
  flushLiquid: null,
  flushPressure: null,
  flushTemp: null,
  flushFlowrate: null,
  bufferBarrierPress: null,
  bufferBarrierFluid: null,
  quenchFluid: null,

  // Fully populated (unlike most golden samples' partial/blank rows).
  sealChamberShaftInspection: [
    { item: "Shaft Run Out", value: "0.03 mm", standard: "Standard 0.050 – 0.076 mm" },
    { item: "Shaft End Play/Axial Float", value: "0.05 mm", standard: "Standard 0.025 – 0.127 mm" },
    { item: "Radial Bearing Fit", value: "0.02 mm", standard: "Standard 0.050 – 0.076 mm" },
    { item: "Squareness/Seal Chamber Face Run Out", value: null, standard: "Limits refer to seal manual" },
    { item: "Seal Chamber Concentricity Run Out", value: null, standard: "Limits refer to seal manual" },
  ],

  basicSealCondition: "New",
  glandCondition: "Old",
  sleeveCondition: "Old",
  shaftCondition: "New",
  bearingCondition: "New",
  gasketCondition: "New",
  radialBearingNo: null,
  thrustBearingNo: null,

  summaryIntro: "Synthetic Refinery Co invited the service provider to assist in replacing the seal on a test pump.",
  siteActivityIntro: "Site activity carried out on March 15-16, 2026 with following details:",
  siteActivities: [
    { date: "Wednesday, March 15, 2026", activities: ["Work permit.", "Dismantling the pump casing and impeller."] },
    { date: "Sunday, March 16, 2026", activities: ["Work permit.", "Hydrostatic testing on pumps."] },
  ],

  bomCaption: 'Mechanical Seal Assembly SYN13435 Type T48MP Size 1.7/8" (00000000)',
  billOfMaterial: [
    { no: 1, partName: "Mating Ring", qty: 1, workRequired: "Replace" },
    { no: 10, partName: "Sleeve", qty: 1, workRequired: "Clean, reuse" },
    // The genuinely-new, non-enum disposition value found on the real
    // 702-P-2 report -- a free-text repair narrative, never forced into
    // Replace/Clean-reuse.
    { no: 12, partName: "Gland Plate", qty: 1, workRequired: "Clean, add Pin Mating Ring, and reuse" },
  ],

  glandObservationNote: "Fill following observation list if gland is reused.",
  glandObservation: [
    { item: "Inboard Side / Outboard Side re-used", checked: true },
    { item: "Corrosion", checked: false },
  ],
  sleeveObservationNote: "Fill following observation list if sleeve is reused.",
  sleeveObservation: [
    { item: "Inboard Side / Outboard Side re-used", checked: true },
    { item: "Deposits", checked: true },
  ],
  retainerDiscObservationNote: "Fill following observation list if retainer / disc is reused.",
  retainerDiscObservation: [{ item: "Inboard Side / Outboard Side re-used", checked: false }],
  cartridgeDriveCollarObservationNote: "Fill following observation list if drive collar is reused.",
  cartridgeDriveCollarObservation: [{ item: "Distortion", checked: false }],

  signatures: [
    { id: 1, company: "Synthetic Service Co", name: "Synthetic Technician", title: "Service", date: "16-03-2026" },
    { id: 2, company: "Synthetic Service Co", name: "Synthetic Engineer", title: "Service Eng.", date: "16-03-2026" },
    { id: 3, company: "Synthetic Customer Co", name: "Synthetic Reviewer", title: "Technician II RE", date: "16-03-2026" },
    { id: 4, company: "Synthetic Customer Co", name: "Synthetic Inspector", title: "Jr. Eng I RE Insp", date: "16-03-2026" },
  ],

  sourceDocumentName: "SYNTHETIC FIXTURE 702-P-2 PATTERN.pdf",
  postInstallationReadings: null,
};

export const goldenStructuralFixtures = [
  sparePatternFixture,
  deOnlyMultiDayReadingsFixture,
  dualPositionThreeDateGroupsFixture,
  freeTextDispositionFixture,
];
