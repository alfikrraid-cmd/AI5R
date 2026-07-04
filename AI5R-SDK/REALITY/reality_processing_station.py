from copy import deepcopy
import re


class RealityProcessingStation:
    def __init__(self, station_id="reality-processing-station"):
        self.station_id = station_id
        self.station_type = "reality_processing"

    def process(self, reality):
        if reality.get("object_type") != "reality":
            raise ValueError("Input must be a Reality Object")

        processed = deepcopy(reality)

        raw_content = processed.get("raw_content", "")
        payload = processed.get("payload", {})

        asset = payload.get("asset") or self._extract_asset(raw_content)

        measurements = payload.get("measurements", {})
        vibration = measurements.get("vibration") or self._extract_vibration(raw_content)
        temperature = measurements.get("temperature") or self._extract_temperature(raw_content)

        findings = list(payload.get("findings", []))

        content_lower = raw_content.lower()

        if "seal leakage" in content_lower or "seal_leakage" in content_lower:
            findings.append("seal_leakage")

        if "bearing" in content_lower:
            findings.append("bearing_issue")

        if vibration is not None and vibration >= 10:
            findings.append("high_vibration")

        if temperature is not None and temperature >= 90:
            findings.append("high_temperature")

        findings = list(dict.fromkeys(findings))

        processed["asset"] = asset
        processed["measurements"] = {
            "vibration": vibration,
            "temperature": temperature,
        }
        processed["findings"] = findings
        processed["status"] = "processed"

        processed["payload"] = {
            **payload,
            "asset": asset,
            "measurements": processed["measurements"],
            "findings": findings,
        }

        return processed

    def adapt(self, reality):
        return self.process(reality)

    def _extract_asset(self, content):
        match = re.search(r"\bP-\d+\b", content)
        return match.group(0) if match else None

    def _extract_vibration(self, content):
        match = re.search(r"Vibration\s+([\d.]+)", content, re.IGNORECASE)
        return float(match.group(1)) if match else None

    def _extract_temperature(self, content):
        match = re.search(r"temperature\s+([\d.]+)", content, re.IGNORECASE)
        return int(float(match.group(1))) if match else None
