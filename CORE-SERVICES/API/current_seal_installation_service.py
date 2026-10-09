"""Current Mechanical Seal Installation Service for LTSA.

Provides business logic for querying current mechanical seal installations on pumps.
Enforces:
- Authoritative installation evidence only.
- Never substitutes configured/design seal.
- Never substitutes drawing applicability.
- Organizes positions by shaft position (DE, NDE for BB pumps; SINGLE for OH pumps).
- Surfaces review/unresolved records in unpositioned_evidence.
- For pumps with no installation evidence, exposes topology-aware empty positions
  (SINGLE for OH, DE/NDE for BB) with resolution_status='NO_AUTHORITATIVE_EVIDENCE'
  and installed_seal=null, without fabricating positions if topology is unknown.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .current_seal_installation_repository import (
    CurrentSealInstallationRepositoryProtocol,
)


class CurrentSealInstallationService:
    """Service for resolving and serving authoritative Current Seal Installations."""

    def __init__(
        self,
        repository: CurrentSealInstallationRepositoryProtocol,
        pump_gateway: Any = None,
        asset_registry_repository: Any = None,
    ) -> None:
        self.repository = repository
        self.pump_gateway = pump_gateway
        self.asset_registry_repository = asset_registry_repository

    def _resolve_pump(self, pump_tag: str) -> Optional[Dict[str, Any]]:
        """Resolve pump details from PumpGateway or AssetRegistryRepository."""
        pump_data = None
        if self.pump_gateway is not None:
            try:
                resp = self.pump_gateway.get_pump(pump_tag)
                if isinstance(resp, dict) and resp.get("success") and isinstance(resp.get("data"), dict):
                    pump_data = resp.get("data")
            except Exception:
                pump_data = None

        if pump_data is None and self.asset_registry_repository is not None:
            try:
                asset = self.asset_registry_repository.get_asset(pump_tag)
                if asset is not None:
                    pump_data = asset
            except Exception:
                pump_data = None

        return pump_data

    def get_current_installation(self, pump_tag: str) -> Optional[Dict[str, Any]]:
        """Retrieve authoritative current mechanical seal installation for a pump.

        Returns None if the pump does not exist in the pump registry / asset registry.
        Never substitutes configured/design seal or drawing applicability.
        """
        pump = self._resolve_pump(pump_tag)
        if pump is None:
            return None

        pump_type = (pump.get("pump_type") or "").strip()
        active_records = self.repository.get_active_by_pump_tag(pump_tag)

        positions: Dict[str, Dict[str, Any]] = {}
        unpositioned_evidence: List[Dict[str, Any]] = []

        has_active_confirmed = False

        for rec in active_records:
            side = rec.get("equipment_side")
            res_status = rec.get("resolution_status")

            entry = {
                "equipment_side": side,
                "seal_type": rec.get("seal_type"),
                "seal_size": rec.get("seal_size"),
                "drawing_no": rec.get("drawing_no"),
                "material_code": rec.get("material_code"),
                "assembly_gpn": rec.get("assembly_gpn"),
                "source_type": rec.get("source_type"),
                "source_reference": rec.get("source_reference"),
                "source_date": str(rec.get("source_date")) if rec.get("source_date") is not None else None,
                "resolution_status": res_status,
                "confidence_status": rec.get("confidence_status"),
                "installed_at": str(rec.get("installed_at")) if rec.get("installed_at") is not None else None,
                "installed_seal": {
                    "seal_type": rec.get("seal_type"),
                    "seal_size": rec.get("seal_size"),
                    "drawing_no": rec.get("drawing_no"),
                    "material_code": rec.get("material_code"),
                    "assembly_gpn": rec.get("assembly_gpn"),
                },
            }

            if res_status == "CONFIRMED" and side in ("SINGLE", "DE", "NDE"):
                positions[side] = entry
                has_active_confirmed = True
            else:
                unpositioned_evidence.append(entry)

        # Topology-aware expected position handling for empty positions
        upper_type = pump_type.upper()
        if "BB" in upper_type:
            # BB dual-seal architecture expects DE and NDE
            for expected_side in ("DE", "NDE"):
                if expected_side not in positions:
                    positions[expected_side] = {
                        "equipment_side": expected_side,
                        "resolution_status": "NO_AUTHORITATIVE_EVIDENCE",
                        "installed_seal": None,
                    }
        elif upper_type in ("OH", "OH2") or "OH" in upper_type:
            # OH single-seal architecture expects SINGLE
            if "SINGLE" not in positions:
                positions["SINGLE"] = {
                    "equipment_side": "SINGLE",
                    "resolution_status": "NO_AUTHORITATIVE_EVIDENCE",
                    "installed_seal": None,
                }
        else:
            # Unknown pump topology: do not fabricate positions
            pass

        # Overall status determination
        confirmed_positions = [
            side for side, pos in positions.items()
            if pos.get("resolution_status") == "CONFIRMED" and pos.get("installed_seal") is not None
        ]

        if "BB" in upper_type:
            if "DE" in confirmed_positions and "NDE" in confirmed_positions:
                status = "CONFIRMED"
            elif confirmed_positions:
                status = "PARTIAL"
            elif unpositioned_evidence:
                status = "REVIEW_REQUIRED"
            else:
                status = "NO_CURRENT_RECORD"
        elif upper_type in ("OH", "OH2") or "OH" in upper_type:
            if "SINGLE" in confirmed_positions:
                status = "CONFIRMED"
            elif unpositioned_evidence:
                status = "REVIEW_REQUIRED"
            else:
                status = "NO_CURRENT_RECORD"
        else:
            if confirmed_positions:
                status = "CONFIRMED"
            elif unpositioned_evidence:
                status = "REVIEW_REQUIRED"
            else:
                status = "NO_CURRENT_RECORD"

        result = {
            "success": True,
            "pump_tag": pump_tag,
            "pump_type": pump_type,
            "status": status,
            "positions": positions,
            "unpositioned_evidence": unpositioned_evidence,
            "data": {
                "pump_tag": pump_tag,
                "pump_type": pump_type,
                "status": status,
                "positions": positions,
                "unpositioned_evidence": unpositioned_evidence,
            },
        }

        return result


__all__ = ["CurrentSealInstallationService"]
