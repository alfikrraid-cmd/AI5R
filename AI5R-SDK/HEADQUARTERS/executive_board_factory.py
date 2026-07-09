from HEADQUARTERS.board import ExecutiveBoard
from HEADQUARTERS.executive import Executive


class ExecutiveBoardFactory:
    EXECUTIVES = [
        {
            "executive_id": "CEO",
            "name": "Raid",
            "title": "Chief Executive Officer",
            "department": "Executive",
            "responsibilities": [
                "Vision",
                "Strategy",
                "Final Executive Decision",
                "Mission Approval",
            ],
            "motto": "Build value. Not just software.",
        },
        {
            "executive_id": "CTO",
            "name": "Jazari",
            "title": "Chief Technology Officer",
            "department": "Technology",
            "responsibilities": [
                "Architecture",
                "Engineering",
                "Digital Factory",
                "Quality",
            ],
            "motto": "Think before coding.",
        },
        {
            "executive_id": "CFO",
            "name": "Graham",
            "title": "Chief Financial Officer",
            "department": "Finance",
            "responsibilities": [
                "Finance",
                "Accounting",
                "ROI",
                "Budget",
            ],
            "motto": "Every decision has a financial consequence.",
        },
        {
            "executive_id": "CLO",
            "name": "Hakim",
            "title": "Chief Legal Officer",
            "department": "Legal",
            "responsibilities": [
                "Compliance",
                "Governance",
                "Contracts",
                "Risk",
            ],
            "motto": "Every decision must be lawful, ethical and accountable.",
        },
        {
            "executive_id": "COO",
            "name": "Orion",
            "title": "Chief Operating Officer",
            "department": "Operations",
            "responsibilities": [
                "Operations",
                "Delivery",
                "Execution",
                "Projects",
            ],
            "motto": "Execution creates results.",
        },
        {
            "executive_id": "CMO",
            "name": "Nova",
            "title": "Chief Marketing Officer",
            "department": "Marketing",
            "responsibilities": [
                "Marketing",
                "Brand",
                "Growth",
                "Customer Acquisition",
            ],
            "motto": "Attention is earned. Trust is built.",
        },
        {
            "executive_id": "CHRO",
            "name": "Hadi",
            "title": "Chief Human Resources Officer",
            "department": "Workforce",
            "responsibilities": [
                "Recruitment",
                "Performance",
                "Skills",
                "Culture",
            ],
            "motto": "Great organizations are built by growing people.",
        },
        {
            "executive_id": "CKO",
            "name": "Sofia",
            "title": "Chief Knowledge Officer",
            "department": "Knowledge",
            "responsibilities": [
                "Knowledge",
                "Learning",
                "Experience",
                "Knowledge Distribution",
            ],
            "motto": "Knowledge grows when it is shared.",
        },
    ]

    def create(self) -> ExecutiveBoard:
        board = ExecutiveBoard()

        for data in self.EXECUTIVES:
            board.register(Executive(**data))

        return board
