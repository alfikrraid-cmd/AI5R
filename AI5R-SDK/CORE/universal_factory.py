from CORE.artifact import Artifact
from CORE.SPECIFICATION import Specification, SpecificationStatus


class UniversalFactory:

    def manufacture(
        self,
        specification: Specification,
    ):

        if specification.status not in [
            SpecificationStatus.APPROVED,
            SpecificationStatus.FROZEN,
        ]:
            return {
                "status": "REJECTED",
                "reason": "Specification must be APPROVED or FROZEN before manufacturing",
                "artifact": None,
            }

        artifact = Artifact(
            artifact_type=specification.specification_type,
            artifact_name=specification.specification_name,
            version=specification.version,
            metadata={
                "specification_id": specification.specification_id,
                **specification.metadata,
            },
        )

        artifact.manufacture()

        return {
            "status": "MANUFACTURED",
            "specification": specification,
            "artifact": artifact,
        }
