class KnowledgeMatchingEngine:
    """
    LTSA-007 Knowledge Matching Engine

    Match structured findings against known maintenance knowledge.
    """

    RULES = {
        frozenset(["seal_leakage"]): {
            "priority": "MEDIUM",
            "recommendation": [
                "Inspect mechanical seal"
            ],
        },
        frozenset(["bearing_issue"]): {
            "priority": "HIGH",
            "recommendation": [
                "Replace bearing"
            ],
        },
        frozenset(["seal_leakage", "bearing_issue"]): {
            "priority": "CRITICAL",
            "recommendation": [
                "Replace bearing",
                "Replace seal",
                "Perform alignment inspection"
            ],
        },
    }

    def match(self, processed):
        findings = frozenset(processed.get("findings", []))

        result = self.RULES.get(findings)

        if result is None:
            return {
                "priority": "UNKNOWN",
                "recommendation": [],
            }

        return result
