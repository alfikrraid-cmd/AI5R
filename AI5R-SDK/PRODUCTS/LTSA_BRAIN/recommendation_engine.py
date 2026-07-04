class RecommendationEngine:
    """
    LTSA-008 Recommendation Engine

    Convert matched maintenance knowledge into actionable recommendation.
    """

    def recommend(self, asset, processed, matched_knowledge):
        if not asset:
            asset = processed.get("asset")

        priority = matched_knowledge.get("priority", "UNKNOWN")
        base_recommendations = matched_knowledge.get("recommendation", [])

        actions = list(base_recommendations)

        measurements = processed.get("measurements", {})

        vibration = measurements.get("vibration")
        temperature = measurements.get("temperature")

        if vibration is not None and vibration >= 10:
            actions.append("Perform vibration analysis")

        if temperature is not None and temperature >= 90:
            actions.append("Check lubrication and bearing temperature")

        if priority == "CRITICAL":
            actions.append("Schedule maintenance shutdown within 24 hours")

        return {
            "asset": asset,
            "priority": priority,
            "recommendation": actions,
            "status": "recommended",
        }
