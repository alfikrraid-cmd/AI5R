class ComplianceReport:

    def generate(self, component_name, result):

        return {
            "component": component_name,
            "status": "CERTIFIED" if result["valid"] else "REJECTED",
            "score": result["score"],
            "missing": result["missing"],
        }
