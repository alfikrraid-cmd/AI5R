class DecisionPolicyEngine:

    def evaluate(
        self,
        options: list,
    ):

        approved = []

        for option in options:

            if option.get("allowed", True):
                approved.append(option)

        if not approved:
            return {
                "status": "REJECTED",
                "approved_options": [],
            }

        return {
            "status": "APPROVED",
            "approved_options": approved,
        }
