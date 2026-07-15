export function createMissionProposal(missionText) {
  const text = missionText || "Build Restaurant Management System";

  return {
    id: "MISSION-0001",
    title: text,
    summary:
      "AI CEO has analyzed your request and prepared the following manufacturing proposal.",
    departments: [
      ["👨‍💼 CEO", "Mission Approval"],
      ["👨‍💻 CTO", "Architecture"],
      ["📋 Project Manager", "Planning"],
      ["⚙ Backend Team", "API Development"],
      ["🧪 QA Team", "Validation"],
      ["🏭 Digital Factory", "Manufacturing"],
    ],
    duration: "4 AI Minutes",
    confidence: "92%",
    deliverables: [
      "Project Workspace",
      "Source Code",
      "API / Application Structure",
      "OpenAPI Documentation",
      "Unit Tests",
      "README",
      "Build Validation",
      "ZIP Package",
    ],
  };
}
