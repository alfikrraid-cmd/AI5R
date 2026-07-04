from .eas_validator import EASValidator


class ArchitectureChecker:

    def __init__(self):
        self.validator = EASValidator()

    def check(self, component):

        result = self.validator.validate(component)

        score = 100

        score -= len(result["missing"]) * 20

        if score < 0:
            score = 0

        return {
            "valid": result["valid"],
            "score": score,
            "missing": result["missing"],
        }
