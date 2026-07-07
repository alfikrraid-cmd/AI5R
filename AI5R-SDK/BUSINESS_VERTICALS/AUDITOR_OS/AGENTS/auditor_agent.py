from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class AuditorAgent:

    agent_id: str
    name: str
    role: str
    capabilities: list[str]
    created_at: str = datetime.now(UTC).isoformat()



class AuditorAgentFactory:


    def create(self):

        return AuditorAgent(

            agent_id="AUDITOR-001",

            name="AI5R Auditor Agent",

            role="DIGITAL_AUDIT_ASSISTANT",

            capabilities=[

                "DOCUMENT_REVIEW",

                "AUDIT_CHECKLIST",

                "RISK_ANALYSIS",

                "REPORT_GENERATION"

            ]

        )
