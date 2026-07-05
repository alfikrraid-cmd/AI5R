from dataclasses import dataclass, field


@dataclass(frozen=True)
class ManufacturingLineSpec:
    code: str
    name: str
    input_object: str
    output_object: str
    stations: list[str] = field(default_factory=list)


class ACMSManifest:
    system_name = "AI5R Artificial Cognitive Manufacturing System"
    abbreviation = "ACMS"
    principle = "Cognitive objects are manufactured through canonical stations."

    MANUFACTURING_LINES = [
        ManufacturingLineSpec(
            code="RML",
            name="Reality Manufacturing Line",
            input_object="RAW_REALITY",
            output_object="REALITY_OBJECT",
            stations=["Reality Intake Station"],
        ),
        ManufacturingLineSpec(
            code="KML",
            name="Knowledge Manufacturing Line",
            input_object="MEMORY_OBJECT",
            output_object="KNOWLEDGE_OBJECT",
            stations=[
                "Knowledge Extraction Station",
                "Knowledge Classification Station",
                "Knowledge Prioritization Station",
                "Knowledge Relationship Station",
                "Knowledge Conflict Station",
            ],
        ),
        ManufacturingLineSpec(
            code="RGL",
            name="Reasoning Manufacturing Line",
            input_object="KNOWLEDGE_OBJECT",
            output_object="REASONING_OBJECT",
            stations=[
                "Premise Station",
                "Evidence Station",
                "Hypothesis Station",
                "Inference Station",
                "Validation Station",
                "Conclusion Station",
            ],
        ),
        ManufacturingLineSpec(
            code="DML",
            name="Decision Manufacturing Line",
            input_object="REASONING_OBJECT",
            output_object="DECISION_OBJECT",
            stations=["Decision Station"],
        ),
        ManufacturingLineSpec(
            code="EML",
            name="Execution Manufacturing Line",
            input_object="DECISION_OBJECT",
            output_object="ACTION_OBJECT",
            stations=["Execution Station"],
        ),
        ManufacturingLineSpec(
            code="LML",
            name="Learning Manufacturing Line",
            input_object="ACTION_OBJECT",
            output_object="LEARNING_OBJECT",
            stations=["Feedback Station", "Improvement Station"],
        ),
    ]

    @classmethod
    def lines(cls):
        return cls.MANUFACTURING_LINES

    @classmethod
    def contracts(cls):
        return cls.MANUFACTURING_LINES

    @classmethod
    def line_codes(cls):
        return [line.code for line in cls.MANUFACTURING_LINES]

    @classmethod
    def find_line(cls, code: str):
        for line in cls.MANUFACTURING_LINES:
            if line.code == code:
                return line
        return None
