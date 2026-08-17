/**
 * MWO-LTSA-056 -- Installation Workspace, canonical source data.
 *
 * This is a full, literal transcription of ONE real, signed engineering
 * document: "SCAN 001 INSTALLATION REPORT 211-P-14B.pdf" (PT Tommy Adji
 * Prasetyo / John Crane, Report No. 001/INSTL /TAP/01-2026, for PT Kilang
 * Pertamina Internasional RU II Dumai). Per this MWO's explicit rule --
 * "If a field exists in the report, the UI must support it. If a field
 * does not exist, do NOT create one." -- every field below traces to one
 * printed field on the report, and no field on the report was dropped.
 *
 * No backend, no API -- like sampleDocuments.js/sampleDrawings.js, this
 * IS the canonical data (not a fetch-path fixture): Installation has no
 * registry/backend anywhere in the repository, and this MWO does not add
 * one. Unlike those files (which back a real, currently-empty backend
 * table), this single record is the actual, permanent content --
 * InstallationWorkspace.jsx defaults to it directly (disclosed in that
 * file's own header comment) rather than to an empty array, because
 * showing it IS the point of this MWO, not a placeholder for missing
 * data.
 *
 * Transcription discipline (never fabricate, never silently correct):
 * - A printed "-" is transcribed as `null` (no value provided), the same
 *   convention every other LTSA sample-data file already uses.
 * - Two fields the source report itself prints with an apparent clerical
 *   typo are transcribed EXACTLY as printed, not silently corrected --
 *   silently editing an official signed engineering document's asserted
 *   values would be a bigger integrity risk than leaving the typo
 *   visible: `sealArrangement: "Non-Cartridge Sigle Seal"` (page 1) and
 *   the Gland observation item `"Flus Port Clogged"` (page 3).
 * - Signatory 3's handwritten name is not legibly transcribable from the
 *   scan -- rather than guess and risk misattributing a real person's
 *   name, it is left `null` (renders "--", the same null-for-unknown
 *   convention `pressureLimit: null` etc. already establish elsewhere in
 *   this codebase). Their printed Title and Date ARE legible and are
 *   transcribed.
 * - The signature block's own printed field label is a clerical typo
 *   ("Tittle"). This is a UI label being authored fresh, not a
 *   transcribed report VALUE (unlike the two cases above) -- it is
 *   rendered correctly as "Title" in InstallationOpenDesignView.jsx, with
 *   this same disclosure repeated at that call site.
 */
const sampleInstallations = [
  {
    id: "INSTL-001-2026",

    // REPORT INFORMATION (page 1)
    reportNo: "001/INSTL /TAP/01-2026",
    tsoNo: null,
    date: "January 06, 2026",
    customer: "PT Kilang Pertamina Internasional RU II Dumai",
    address: "Jl. Raya Kilang Putri Tujuh, Tanjung Palas, Dumai Timur, Riau 28815",
    plant: "HCC",
    unit: "Fraksinasi",
    poNo: "4500024221",
    packingListNo: null,
    location: "Workshop",

    // GENERAL DATA (page 1)
    equipmentMfr: "Guinard S.A.",
    modelType: "SMK-10x12x18",
    size: "10x12x18",
    configuration: null,
    serialNo: null,
    plantEquipNo: "211-P-14B",
    pumpType: "OH2",
    shaftSpeed: "1500 rpm",
    rotation: "CCW",
    sealManufacture: "John Crane",
    sealType: "T15W",
    sealArrangement: "Non-Cartridge Sigle Seal", // verbatim, see header disclosure
    sealSize: "3.1/4\"",
    materialCode: "1K1K",
    drawingNo: "E12914",
    sealLocation: "DE",
    // MWO-LTSA-068 -- seal_code is a real, nullable FK column on
    // installation_report (CANONICAL_SCHEMA.sql); null here matches the
    // real seed row exactly -- this report carries no seal_registry
    // identifier, only descriptive text (sealType/sealManufacture above).
    sealCode: null,

    // SERVICE / OPERATION CONDITIONS (page 1)
    liquid: "Diesel Around Pump",
    temperatureRange: "329°C",
    specificGravity: "0.601",
    viscosity: "0.24 cP",
    flashPoint: null,
    boilingPoint: null,
    freezePoint: null,
    vaporPress: null,
    dischargePress: "6.38 kg/cm²g",
    suctionPress: "2.26-4.86 kg/cm²g",
    differentialPress: null,
    stuffingBoxPress: null,
    sealPress: "4.12 kg/cm²g",
    corrosionErosionBy: null,
    apiPlan: "22/62",
    flushLiquid: null,
    flushPressure: null,
    flushTemp: null,
    flushFlowrate: null,
    bufferBarrierPress: null,
    bufferBarrierFluid: null,
    quenchFluid: "Steam",

    // SEAL CHAMBER & SHAFT INSPECTION (page 1) -- each carries a measured
    // value AND the report's own printed standard/limit reference.
    sealChamberShaftInspection: [
      { item: "Shaft Run Out", value: "0.01 mm", standard: "Standard 0.050 – 0.076 mm" },
      { item: "Shaft End Play/Axial Float", value: "0.06 mm", standard: "Standard 0.025 – 0.127 mm" },
      { item: "Radial Bearing Fit", value: "0.02 mm", standard: "Standard 0.050 – 0.076 mm" },
      { item: "Squareness/Seal Chamber Face Run Out", value: null, standard: "Limits refer to seal manual" },
      { item: "Seal Chamber Concentricity Run Out", value: null, standard: "Limits refer to seal manual" },
    ],

    // NOTE (page 2)
    basicSealCondition: "New",
    glandCondition: "Old",
    sleeveCondition: "New",
    shaftCondition: "Old",
    bearingCondition: "New",
    gasketCondition: "New",
    radialBearingNo: null,
    thrustBearingNo: null,

    // SUMMARY (page 2)
    summaryIntro:
      "PT Kilang Pertamina Internasional RU II Dumai invited PT Tommy Adji Prasetyo to assist in replacing and troubleshooting the seal on the pump tag number 211-P-14B.",
    siteActivityIntro: "Site activity carried out on January 06, 2026 with following detail:",
    // MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 -- site
    // activities are grouped by date, never a flat string list: 3 of 5
    // golden-sample reports print multiple dated field-activity sessions
    // (e.g. "Friday-Saturday, January 23-24, 2026" as one group, a
    // separate "Wednesday, January 28, 2026" group), and flattening loses
    // which activity happened on which date -- meaningful engineering
    // chronology (a monitoring visit's activities are the direct cause of
    // that same day's postInstallationReadings). This report is
    // single-day, so it is one group; the shape itself is uniform across
    // every report regardless of day count.
    siteActivities: [
      {
        date: "January 06, 2026",
        activities: [
          "Work permit.",
          "Dismantling the pump casing and impeller.",
          "Dismantling the gland plate from the pump stuffing box.",
          "Inspection and cleaning of mechanical seal parts.",
          "Check mechanical seal existing.",
          "Measurement of shaft run out, shaft end play, and radial bearing fit.",
          "Visual check and cleaning of the stuffing box condition.",
          "Assembly of mechanical seal parts.",
          "Mechanical seal face contact measurement.",
          "Install the mechanical seal on the stuffing box.",
          "Check the flushing, quenching, and drain line.",
          "Assembly of stuffing box, impeller, and pump casing.",
          "Check the pump rotation.",
          "Hydrostatic testing on pumps.",
        ],
      },
    ],

    // BILL OF MATERIAL (page 2)
    bomCaption: "Mechanical Seal Assembly E12914 Type T15W Size 3.1/4\" (89430204)",
    billOfMaterial: [
      { no: 1, partName: "Mating Ring", qty: 1, workRequired: "Replace" },
      { no: 2, partName: "Mating Ring Gasket", qty: 2, workRequired: "Replace" },
      { no: 3, partName: "Bellows Assembly", qty: 1, workRequired: "Replace" },
      { no: 4, partName: "Wedge", qty: 1, workRequired: "Replace" },
      { no: 5, partName: "Set Screw", qty: 3, workRequired: "Replace" },
      { no: 6, partName: "Cap Screw", qty: 8, workRequired: "Replace" },
      { no: 7, partName: "Sleeve", qty: 1, workRequired: "Replace" },
      { no: 8, partName: "Gasket", qty: 1, workRequired: "Replace" },
      { no: 9, partName: "Adaptor Plate", qty: 1, workRequired: "Clean, reuse" },
      { no: 10, partName: "Gasket", qty: 1, workRequired: "Replace" },
      { no: 11, partName: "Clamp Plate", qty: 1, workRequired: "Clean, reuse" },
    ],

    // OBSERVATION CHECKLISTS (page 3-4) -- `checked` transcribes the
    // report's own checkbox marks exactly (only Gland's first item is
    // checked; every other item across all four groups is unchecked).
    glandObservationNote: "Fill following observation list if gland is reused.",
    glandObservation: [
      { item: "Inboard Side / Outboard Side re-used", checked: true },
      { item: "Corrosion", checked: false },
      { item: "Erosion", checked: false },
      { item: "Mechanical Damage", checked: false },
      { item: "Anti-Rotation Pin Broken", checked: false },
      { item: "Missing Bushing", checked: false },
      { item: "Flus Port Clogged", checked: false }, // verbatim, see header disclosure
      { item: "Quench / Buffer Port Clogged", checked: false },
      { item: "Contact with Driver Collar", checked: false },
      { item: "Contact with Pumping Ring", checked: false },
      { item: "Contact with Sleeve", checked: false },
    ],

    sleeveObservationNote: "Fill following observation list if sleeve is reused.",
    sleeveObservation: [
      { item: "Inboard Side / Outboard Side re-used", checked: false },
      { item: "Heat Discoloration", checked: false },
      { item: "Fretting", checked: false },
      { item: "Corrosion", checked: false },
      { item: "Deposits", checked: false },
      { item: "Signs of O-Ring Hang up", checked: false },
      { item: "Signs of Slipping", checked: false },
      { item: "Worn Hard Coating", checked: false },
      { item: "Marking Under Sliding Pack", checked: false },
      { item: "Contact with Mating Ring", checked: false },
      { item: "Contact with Bushing", checked: false },
      { item: "Contact with Gland", checked: false },
      { item: "Deformed Setting Holes", checked: false },
    ],

    retainerDiscObservationNote: "Fill following observation list if retainer / disc is reused.",
    retainerDiscObservation: [
      { item: "Inboard Side / Outboard Side re-used", checked: false },
      { item: "Wear on Drive Section", checked: false },
      { item: "Wear on Disc Slot", checked: false },
      { item: "Rubbing on Retainer OD", checked: false },
      { item: "Rubbing on Retainer ID", checked: false },
      { item: "Signs of Slipping", checked: false },
      { item: "Corrosion", checked: false },
      { item: "Pumping Ring Damage", checked: false },
      { item: "Contact with Bushing", checked: false },
    ],

    cartridgeDriveCollarObservationNote: "Fill following observation list if drive collar is reused.",
    cartridgeDriveCollarObservation: [
      { item: "Distortion", checked: false },
      { item: "Incorrect Setting Postition", checked: false },
      { item: "Signs of Slipping", checked: false },
      { item: "Contact with Gland", checked: false },
      { item: "Scoring or Erosion", checked: false },
      { item: "Thread Damage", checked: false },
    ],

    // SIGNATURES (page 4). Signatory 3's handwritten name is illegible in
    // the scan -- left `null` rather than guessed; see header disclosure.
    signatures: [
      { id: 1, company: "PT Tommy Adji Prasetyo", name: "Rizky Trinoviandi", title: "Service", date: "7/01/2026" },
      { id: 2, company: "PT Tommy Adji Prasetyo", name: "Muh Taufik", title: "Service Engineer", date: "07/01/2026" },
      { id: 3, company: "PT KPI RU II Dumai", name: null, title: "Technicion I/RE", date: "07-01-2026" },
      { id: 4, company: "PT KPI RU II Dumai", name: "Thomas R.", title: "Jr. Eng / RE Insp", date: "07-01-2026" },
    ],

    // MWO-LTSA-068 -- source_document_name is a real, already-existing
    // NOT NULL column on installation_report (the scanned source file's
    // own name); the "Attachments" section reuses this single real fact
    // rather than inventing a file-attachment list this schema doesn't
    // have.
    sourceDocumentName: "SCAN 001 INSTALLATION REPORT 211-P-14B.pdf",

    // MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 -- this
    // report carries no post-installation Condition Monitoring table;
    // null (not []) honestly means "no such section on this report", not
    // "a section with zero readings" -- see installation_report's own
    // column comment (CANONICAL_SCHEMA.sql) for the full field shape.
    postInstallationReadings: null,
  },
];

export default sampleInstallations;
