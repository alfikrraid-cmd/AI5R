from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class EducationKnowledge:

    knowledge_id: str
    domain: str
    topics: list[str]
    created_at: str = datetime.now(UTC).isoformat()



class SchoolKnowledgeRegistry:


    def __init__(self):

        self.knowledge = {}



    def register(
        self,
        knowledge: EducationKnowledge
    ):

        self.knowledge[
            knowledge.knowledge_id
        ] = knowledge


        return {

            "status":"REGISTERED",

            "knowledge_id":
            knowledge.knowledge_id

        }



    def get(
        self,
        knowledge_id: str
    ):

        return self.knowledge.get(
            knowledge_id
        )
