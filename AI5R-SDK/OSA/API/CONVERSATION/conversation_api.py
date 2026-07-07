from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class ConversationResponse:

    message: str
    recommendation: str
    created_at: str = datetime.now(UTC).isoformat()



class OSAConversationAPI:


    def process(
        self,
        message: str
    ):


        return ConversationResponse(

            message=
            f"Understanding request: {message}",

            recommendation=
            "Analyze opportunity and generate AI system blueprint"

        )
