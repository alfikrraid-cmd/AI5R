import { describe, expect, it } from "vitest";
import { mapInstallationRecord } from "./installationMapping";
import sampleInstallations from "../data/sampleInstallations";

// MWO-LTSA-060 -- the raw shape a real installation_report row takes once
// it comes back through InstallationGateway/the /api/ltsa/installations
// response (snake_case columns, matching
// BP-INSTALLATION/DATABASE/001_create_table.sql and the real seed row in
// 002_seed.sql byte-for-byte).
const RAW_RECORD = {
  installation_code: "INSTL-001-2026",
  report_no: "001/INSTL /TAP/01-2026",
  tso_no: null,
  report_date: "January 06, 2026",
  customer: "PT Kilang Pertamina Internasional RU II Dumai",
  address: "Jl. Raya Kilang Putri Tujuh, Tanjung Palas, Dumai Timur, Riau 28815",
  plant: "HCC",
  unit: "Fraksinasi",
  po_no: "4500024221",
  packing_list_no: null,
  location: "Workshop",

  equipment_mfr: "Guinard S.A.",
  model_type: "SMK-10x12x18",
  size: "10x12x18",
  configuration: null,
  serial_no: null,
  plant_equip_no: "211-P-14B",
  pump_type: "OH2",
  shaft_speed: "1500 rpm",
  rotation: "CCW",
  seal_manufacture: "John Crane",
  seal_type: "T15W",
  seal_arrangement: "Non-Cartridge Sigle Seal",
  seal_size: "3.1/4\"",
  material_code: "1K1K",
  drawing_no: "E12914",
  seal_location: "DE",
  seal_code: null,

  liquid: "Diesel Around Pump",
  temperature_range: "329°C",
  specific_gravity: "0.601",
  viscosity: "0.24 cP",
  flash_point: null,
  boiling_point: null,
  freeze_point: null,
  vapor_press: null,
  discharge_press: "6.38 kg/cm²g",
  suction_press: "2.26-4.86 kg/cm²g",
  differential_press: null,
  stuffing_box_press: null,
  seal_press: "4.12 kg/cm²g",
  corrosion_erosion_by: null,
  api_plan: "22/62",
  flush_liquid: null,
  flush_pressure: null,
  flush_temp: null,
  flush_flowrate: null,
  buffer_barrier_press: null,
  buffer_barrier_fluid: null,
  quench_fluid: "Steam",

  seal_chamber_shaft_inspection: [
    { item: "Shaft Run Out", value: "0.01 mm", standard: "Standard 0.050 – 0.076 mm" },
    { item: "Shaft End Play/Axial Float", value: "0.06 mm", standard: "Standard 0.025 – 0.127 mm" },
    { item: "Radial Bearing Fit", value: "0.02 mm", standard: "Standard 0.050 – 0.076 mm" },
    { item: "Squareness/Seal Chamber Face Run Out", value: null, standard: "Limits refer to seal manual" },
    { item: "Seal Chamber Concentricity Run Out", value: null, standard: "Limits refer to seal manual" },
  ],

  basic_seal_condition: "New",
  gland_condition: "Old",
  sleeve_condition: "New",
  shaft_condition: "Old",
  bearing_condition: "New",
  gasket_condition: "New",
  radial_bearing_no: null,
  thrust_bearing_no: null,

  summary_intro:
    "PT Kilang Pertamina Internasional RU II Dumai invited PT Tommy Adji Prasetyo to assist in replacing and troubleshooting the seal on the pump tag number 211-P-14B.",
  site_activity_intro: "Site activity carried out on January 06, 2026 with following detail:",
  site_activities: [
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

  bom_caption: "Mechanical Seal Assembly E12914 Type T15W Size 3.1/4\" (89430204)",
  bill_of_material: [
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

  gland_observation_note: "Fill following observation list if gland is reused.",
  gland_observation: [
    { item: "Inboard Side / Outboard Side re-used", checked: true },
    { item: "Corrosion", checked: false },
    { item: "Erosion", checked: false },
    { item: "Mechanical Damage", checked: false },
    { item: "Anti-Rotation Pin Broken", checked: false },
    { item: "Missing Bushing", checked: false },
    { item: "Flus Port Clogged", checked: false },
    { item: "Quench / Buffer Port Clogged", checked: false },
    { item: "Contact with Driver Collar", checked: false },
    { item: "Contact with Pumping Ring", checked: false },
    { item: "Contact with Sleeve", checked: false },
  ],

  sleeve_observation_note: "Fill following observation list if sleeve is reused.",
  sleeve_observation: [
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

  retainer_disc_observation_note: "Fill following observation list if retainer / disc is reused.",
  retainer_disc_observation: [
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

  cartridge_drive_collar_observation_note: "Fill following observation list if drive collar is reused.",
  cartridge_drive_collar_observation: [
    { item: "Distortion", checked: false },
    { item: "Incorrect Setting Postition", checked: false },
    { item: "Signs of Slipping", checked: false },
    { item: "Contact with Gland", checked: false },
    { item: "Scoring or Erosion", checked: false },
    { item: "Thread Damage", checked: false },
  ],

  signatures: [
    { id: 1, company: "PT Tommy Adji Prasetyo", name: "Rizky Trinoviandi", title: "Service", date: "7/01/2026" },
    { id: 2, company: "PT Tommy Adji Prasetyo", name: "Muh Taufik", title: "Service Engineer", date: "07/01/2026" },
    { id: 3, company: "PT KPI RU II Dumai", name: null, title: "Technicion I/RE", date: "07-01-2026" },
    { id: 4, company: "PT KPI RU II Dumai", name: "Thomas R.", title: "Jr. Eng / RE Insp", date: "07-01-2026" },
  ],

  source_document_name: "SCAN 001 INSTALLATION REPORT 211-P-14B.pdf",
  post_installation_readings: null,
};

describe("mapInstallationRecord", () => {
  it("maps the real installation_report row into exactly the shape InstallationOpenDesignView.jsx already expects", () => {
    const mapped = mapInstallationRecord(RAW_RECORD);

    expect(mapped.id).toBe("INSTL-001-2026");
    expect(mapped.reportNo).toBe("001/INSTL /TAP/01-2026");
    expect(mapped.plantEquipNo).toBe("211-P-14B");
    expect(mapped.drawingNo).toBe("E12914");
    // MWO-LTSA-068 -- two previously-unmapped, already-existing columns.
    expect(mapped.sealCode).toBeNull();
    expect(mapped.sourceDocumentName).toBe("SCAN 001 INSTALLATION REPORT 211-P-14B.pdf");
    // Two deliberately-preserved clerical typos, never silently corrected.
    expect(mapped.sealArrangement).toBe("Non-Cartridge Sigle Seal");
    expect(mapped.glandObservation.find((o) => o.item === "Flus Port Clogged")).toBeTruthy();
    // Signatory 3's illegible name stays null, never guessed.
    expect(mapped.signatures.find((s) => s.id === 3).name).toBeNull();
  });

  it("produces migration parity: the mapped real DB row equals sampleInstallations.js's own record field-for-field, no fields lost", () => {
    const mapped = mapInstallationRecord(RAW_RECORD);
    const { id: _ignoredId, ...expectedWithoutId } = sampleInstallations[0];
    const { id: _mappedId, ...mappedWithoutId } = mapped;

    expect(mapped.id).toBe(sampleInstallations[0].id);
    expect(mappedWithoutId).toEqual(expectedWithoutId);
  });

  it("defaults every nested array field to [], never null, when the column is null -- InstallationOpenDesignView.jsx calls unguarded .map() on them", () => {
    const sparse = {
      installation_code: "INSTL-002-2026",
      report_no: "002/INSTL /TAP/02-2026",
      source_document_name: "SCAN 002.pdf",
    };

    const mapped = mapInstallationRecord(sparse);

    expect(mapped.sealChamberShaftInspection).toEqual([]);
    expect(mapped.siteActivities).toEqual([]);
    expect(mapped.billOfMaterial).toEqual([]);
    expect(mapped.glandObservation).toEqual([]);
    expect(mapped.sleeveObservation).toEqual([]);
    expect(mapped.retainerDiscObservation).toEqual([]);
    expect(mapped.cartridgeDriveCollarObservation).toEqual([]);
    expect(mapped.signatures).toEqual([]);
    expect(() => mapped.siteActivities.map((x) => x)).not.toThrow();
  });

  it("defaults missing scalar fields to null, never fabricated", () => {
    const sparse = {
      installation_code: "INSTL-002-2026",
      report_no: "002/INSTL /TAP/02-2026",
      source_document_name: "SCAN 002.pdf",
    };

    const mapped = mapInstallationRecord(sparse);

    expect(mapped.customer).toBeNull();
    expect(mapped.plantEquipNo).toBeNull();
    expect(mapped.sealType).toBeNull();
    expect(mapped.sealCode).toBeNull();
  });

  // MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001
  it("maps siteActivities as date-grouped chronology, preserving date and activity order, never a flat string list", () => {
    const mapped = mapInstallationRecord(RAW_RECORD);

    expect(mapped.siteActivities).toHaveLength(1);
    expect(mapped.siteActivities[0].date).toBe("January 06, 2026");
    expect(mapped.siteActivities[0].activities).toHaveLength(14);
    expect(mapped.siteActivities[0].activities[0]).toBe("Work permit.");
    expect(mapped.siteActivities[0].activities[13]).toBe("Hydrostatic testing on pumps.");
  });

  it("maps postInstallationReadings to null (not []) when the report carries no such section", () => {
    const mapped = mapInstallationRecord(RAW_RECORD);
    expect(mapped.postInstallationReadings).toBeNull();
  });

  it("maps postInstallationReadings through verbatim when present, preserving measurement/value/unit/location/DE/NDE", () => {
    const withReadings = {
      ...RAW_RECORD,
      post_installation_readings: [
        {
          measurement: "Mechanical Seal Gland Temperature",
          unit: "°C",
          de: "107",
          nde: "115",
          dateTime: "2026-01-28T10:15:00",
        },
        { measurement: "Connection Condition", de: "v", nde: "v", dateTime: "2026-01-28T10:15:00" },
      ],
    };

    const mapped = mapInstallationRecord(withReadings);

    expect(mapped.postInstallationReadings).toHaveLength(2);
    expect(mapped.postInstallationReadings[0].measurement).toBe("Mechanical Seal Gland Temperature");
    expect(mapped.postInstallationReadings[0].de).toBe("107");
    expect(mapped.postInstallationReadings[0].nde).toBe("115");
  });

  it("defaults postInstallationReadings to null when the column itself is missing/null on a sparse record", () => {
    const sparse = {
      installation_code: "INSTL-002-2026",
      report_no: "002/INSTL /TAP/02-2026",
      source_document_name: "SCAN 002.pdf",
    };

    const mapped = mapInstallationRecord(sparse);
    expect(mapped.postInstallationReadings).toBeNull();
  });
});
