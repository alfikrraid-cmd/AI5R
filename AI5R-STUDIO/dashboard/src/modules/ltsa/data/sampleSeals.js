/**
 * Static engineering sample data for the LTSA Seal Workspace (MWO-UI-006
 * WP-002). No backend, no API — shaped like the canonical `seal_registry`
 * fields (seal_code, seal_name, manufacturer, status, etc.) plus
 * `seal_pump_compatibility`/`seal_interchange_compatibility` cross-
 * references described in the LTSA-BRAIN Constitution, for UI-only
 * demonstration. `compatiblePumps` codes match `samplePumps.js`'s own
 * `code` field, consistent with the two workspaces describing the same
 * plant.
 */
const sampleSeals = [
  {
    code: "SC-001",
    name: "John Crane Type 21",
    type: "Single Mechanical Seal",
    manufacturer: "John Crane",
    compatiblePumps: ["PMP-001", "PMP-002"],
    compatibleSeals: ["SC-002"],
    status: "ACTIVE",
    recommendation: "No action required. In service on both Boiler Feedwater units.",
    knowledgeLinks: ["Installation Report #IR-2201", "Seal Datasheet Type 21"],
  },
  {
    code: "SC-002",
    name: "John Crane Type 1",
    type: "Single Mechanical Seal",
    manufacturer: "John Crane",
    compatiblePumps: [],
    compatibleSeals: ["SC-001"],
    status: "STANDBY",
    recommendation: "Approved interchange for Type 21 — hold as spare stock only.",
    knowledgeLinks: ["Interchange Compatibility Note"],
  },
  {
    code: "SC-003",
    name: "Flowserve ISC2",
    type: "Dual Cartridge Seal",
    manufacturer: "Flowserve",
    compatiblePumps: ["PMP-003"],
    compatibleSeals: [],
    status: "ACTIVE",
    recommendation: "Recommended: purchase additional stock — coverage below threshold.",
    knowledgeLinks: ["Seal Stock Report Q1", "Cooling Tower P&ID Rev.C"],
  },
  {
    code: "SC-004",
    name: "Flowserve-210",
    type: "Cartridge Seal (API Plan 11/21)",
    manufacturer: "Flowserve",
    compatiblePumps: ["PMP-004", "PMP-005"],
    compatibleSeals: [],
    status: "ACTIVE",
    recommendation: "No action required. Standard fit on both Crude Charge Pump units.",
    knowledgeLinks: ["Work Order #WO-4471"],
  },
  {
    code: "SC-005",
    name: "AESSEAL P8",
    type: "Component Seal (API Plan 52)",
    manufacturer: "AESSEAL",
    compatiblePumps: ["PMP-006", "PMP-007"],
    compatibleSeals: [],
    status: "ALERT",
    recommendation: "Recommended: inspect seal flush plan — elevated seal chamber temperature on PMP-006.",
    knowledgeLinks: ["Inspection Sheet #INS-0093", "Seal Flush Plan 52"],
  },
  {
    code: "SC-006",
    name: "Grundfos Cartridge Seal",
    type: "Cartridge Seal",
    manufacturer: "Grundfos",
    compatiblePumps: ["PMP-008"],
    compatibleSeals: [],
    status: "ACTIVE",
    recommendation: "No action required. Monthly churn test passed.",
    knowledgeLinks: ["Fire Protection Test Log"],
  },
  {
    code: "SC-007",
    name: "John Crane 502",
    type: "Dual Pressurized Seal (API Plan 53A)",
    manufacturer: "John Crane",
    compatiblePumps: ["PMP-009", "PMP-010"],
    compatibleSeals: ["SC-008"],
    status: "FAULT",
    recommendation: "Recommended: replace on PMP-009 — repeat seal failures logged (3 in 90 days).",
    knowledgeLinks: ["Failure Report #FR-1187", "Interchange Compatibility Note"],
  },
  {
    code: "SC-008",
    name: "EagleBurgmann HSU",
    type: "Dual Pressurized Seal (API Plan 53A)",
    manufacturer: "EagleBurgmann",
    compatiblePumps: [],
    compatibleSeals: ["SC-007"],
    status: "STANDBY",
    recommendation: "Approved interchange for John Crane 502 — hold as spare stock.",
    knowledgeLinks: ["Interchange Compatibility Note"],
  },
  {
    code: "SC-009",
    name: "Chesterton 155",
    type: "Split Seal",
    manufacturer: "Chesterton",
    compatiblePumps: [],
    compatibleSeals: [],
    status: "STANDBY",
    recommendation: "Warehouse stock. No current pump assignment.",
    knowledgeLinks: [],
  },
  {
    code: "SC-010",
    name: "Burgmann M7N",
    type: "Single Mechanical Seal (API Plan 11)",
    manufacturer: "EagleBurgmann",
    compatiblePumps: [],
    compatibleSeals: [],
    status: "MAINTENANCE",
    recommendation: "Removed for bench inspection following seal face wear finding.",
    knowledgeLinks: ["Maintenance History Log"],
  },
];

export default sampleSeals;
