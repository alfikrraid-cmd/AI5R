from .eas_rules import RULES


class EASValidator:

    def validate(self, component):

        missing = []

        for rule in RULES:
            if not component.get(rule, False):
                missing.append(rule)

        return {
            "valid": len(missing) == 0,
            "missing": missing,
        }
