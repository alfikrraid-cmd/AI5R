from typing import Dict, List


class PumpFindingExtractor:
    def extract(self, report_text: str) -> Dict[str, List[str]]:
        text = report_text.lower()

        findings = {
            "vibration": [],
            "temperature": [],
            "lubrication": [],
            "seal": [],
            "bearing": [],
            "general": [],
        }

        if "vibration" in text or "vibrasi" in text:
            findings["vibration"].append("Vibration issue mentioned in report")

        if "temperature" in text or "temp" in text or "suhu" in text:
            findings["temperature"].append("Temperature condition mentioned in report")

        if "lubrication" in text or "lube" in text or "pelumasan" in text:
            findings["lubrication"].append("Lubrication condition mentioned in report")

        if "seal" in text or "mechanical seal" in text:
            findings["seal"].append("Seal condition mentioned in report")

        if "bearing" in text:
            findings["bearing"].append("Bearing condition mentioned in report")

        if not any(findings.values()):
            findings["general"].append("No specific pump issue keyword detected")

        return findings
