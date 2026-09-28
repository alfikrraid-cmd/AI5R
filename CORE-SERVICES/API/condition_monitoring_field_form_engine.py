"""AI5R — LTSA Condition Monitoring Field Form Ingestion Engine (CM R5B).

Deterministic field-form ingestion pipeline according to frozen R5A contract:
  SOURCE FIELD FORM -> PARSE -> SOURCE PRESERVATION -> ASSET RESOLUTION ->
  CANONICAL PARAMETER MAPPING -> VALUE / STATE VALIDATION -> PREVIEW ->
  READY_TO_APPLY / REVIEW_REQUIRED -> ATOMIC PER-ASSET PERSISTENCE ADAPTER

INVARIANTS & POLICIES:
- CANONICAL_PARAMETERS = 42
- STORAGE TIERS: 20 Legacy parent columns, 20 Child measurements, 2 Child observations.
- ASSET RESOLUTION:
    1. EXACT asset_registry identity (133 recognized exact assets)
    2. EXPLICIT approved alias (15 approved explicit aliases from R5A.1)
    3. REVIEW_REQUIRED (including 5 quarantined Unit 946 assets: 946-P-2D, 946-P-4A, 946-P-4C, 946-P-8A, 946-P-8B)
- AUTO_NORMALIZATION_ALLOWED = NO (prohibit generic rules like A->AR, B->BR, or prefix regex guessing).
- VALUE STATES: VALUE_PRESENT, NOT_APPLICABLE, NOT_INSPECTED, UNKNOWN.
    Invariants: 0 != N/A, N/A != NOT_INSPECTED, UNKNOWN != NOT_INSPECTED, blank != 0.
- CONDITION STATES: NORMAL, MONITOR, ABNORMAL, NOT_APPLICABLE, NOT_INSPECTED, UNKNOWN.
    Condition is distinct from raw measurement value.
- LEAKAGE MODEL: NONE (False), OBSERVED (True).
    OBSERVED leakage does NOT automatically create ltsa_finding.
- FINDING BOUNDARY: AUTO_FINDING_CREATION = NO.
- INGESTION_UNIT = WALKING_ROUND_BATCH, PERSISTENCE_UNIT = INDIVIDUAL_ASSET_CM_READING.
- ATOMICITY: All-or-nothing per asset reading (parent + child measurements).
- PREVIEW: Pure in-memory inspection; never mutates database.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Sequence
import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

try:
    from ltsa_pump_inventory_db_upsert import _sql
except ImportError:
    def _sql(val: Any) -> str:
        if val is None:
            return "NULL"
        if isinstance(val, bool):
            return "TRUE" if val else "FALSE"
        if isinstance(val, (int, float)):
            return str(val)
        escaped = str(val).replace("'", "''")
        return f"'{escaped}'"


# ==============================================================================
# 1. DOMAIN ENUMS & ERROR TAXONOMY
# ==============================================================================

class IngestionState(str, Enum):
    PARSED = "PARSED"
    VALIDATED = "VALIDATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READY_TO_APPLY = "READY_TO_APPLY"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"


class ValueState(str, Enum):
    VALUE_PRESENT = "VALUE_PRESENT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_INSPECTED = "NOT_INSPECTED"
    UNKNOWN = "UNKNOWN"


class ConditionState(str, Enum):
    NORMAL = "NORMAL"
    MONITOR = "MONITOR"
    ABNORMAL = "ABNORMAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_INSPECTED = "NOT_INSPECTED"
    UNKNOWN = "UNKNOWN"


class LeakageState(str, Enum):
    NONE = "NONE"
    OBSERVED = "OBSERVED"


class StorageTier(str, Enum):
    LEGACY_PARENT_TABLE = "LEGACY_PARENT_TABLE"
    CHILD_MEASUREMENT_TABLE = "CHILD_MEASUREMENT_TABLE"
    CHILD_OBSERVATION_TABLE = "CHILD_OBSERVATION_TABLE"


class ErrorCode(str, Enum):
    UNKNOWN_ASSET = "UNKNOWN_ASSET"
    AMBIGUOUS_ASSET = "AMBIGUOUS_ASSET"
    REVIEW_REQUIRED_ASSET = "REVIEW_REQUIRED_ASSET"
    UNKNOWN_PARAMETER = "UNKNOWN_PARAMETER"
    INVALID_VALUE = "INVALID_VALUE"
    INVALID_UNIT = "INVALID_UNIT"
    INVALID_STATE = "INVALID_STATE"
    DUPLICATE_VALUE = "DUPLICATE_VALUE"
    MISSING_REQUIRED_HEADER = "MISSING_REQUIRED_HEADER"
    INAPPLICABLE_VALUE_PRESENT = "INAPPLICABLE_VALUE_PRESENT"


# ==============================================================================
# 2. CANONICAL PARAMETER CONTRACT (42 PARAMETERS)
# ==============================================================================

@dataclass(frozen=True, slots=True)
class CanonicalParameterContract:
    param_id: int
    code: str
    label: str
    data_type: str  # "NUMERIC", "BOOLEAN", "TEXT"
    storage_tier: StorageTier
    target_column: str
    measurement_code_if_child: str | None
    measurement_side: str | None  # "DE", "NDE", or None
    canonical_unit: str
    allowed_units: tuple[str, ...]
    aliases: tuple[str, ...]


_PARAM_CONTRACTS: tuple[CanonicalParameterContract, ...] = (
    # --- GENERAL (4 parameters) ---
    CanonicalParameterContract(
        1, "suction_pressure", "Suction Pressure", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "suction_pressure", None, None,
        "kg/cm2", ("kg/cm2", "kg/cm", "bar", "barg"),
        ("suction pressure", "tekanan suction", "suction press")
    ),
    CanonicalParameterContract(
        2, "suction_temp", "Suction Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "suction_temp", None, None,
        "°C", ("°c", "c", "deg c", "celsius"),
        ("suction temp", "suction temperature", "suhu suction")
    ),
    CanonicalParameterContract(
        3, "discharge_pressure", "Discharge Pressure", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "discharge_pressure", None, None,
        "kg/cm2", ("kg/cm2", "kg/cm", "bar", "barg"),
        ("discharge pressure", "tekanan discharge", "discharge press")
    ),
    CanonicalParameterContract(
        4, "discharge_temp", "Discharge Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "discharge_temp", None, None,
        "°C", ("°c", "c", "deg c", "celsius"),
        ("discharge temp", "discharge temperature", "suhu discharge")
    ),

    # --- DRIVE END (DE) (19 parameters) ---
    CanonicalParameterContract(
        5, "mechanical_seal_leak_de", "Drive End Mechanical Seal Leakage", "BOOLEAN",
        StorageTier.LEGACY_PARENT_TABLE, "mechanical_seal_leak_de", None, "DE",
        "NONE", ("none", "observed", "y/n", "boolean", ""),
        ("mechanical seal leakage de", "mechseal leak de", "seal leakage de")
    ),
    CanonicalParameterContract(
        6, "seal_gland_temp_de", "Drive End Seal Gland Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "seal_gland_temp_de", None, "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("seal gland temp de", "seal gland temperature de", "gland temp de")
    ),
    CanonicalParameterContract(
        7, "flushing_in_temp_de", "Drive End Flush In Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "flushing_in_temp_de", None, "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("flushing in temp de", "flushing in temperature de", "flushing temp de")
    ),
    CanonicalParameterContract(
        8, "quench_temp_de", "Drive End Quench In Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "quench_temp_de", None, "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("quench in temp de", "quench in temperature de", "quench temp de", "quinch in temperature de")
    ),
    CanonicalParameterContract(
        9, "stuffing_box_temp_de", "Drive End Stuffing Box Out Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "stuffing_box_temp_de", None, "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("stuffing box out temp de", "stuffing box out temperature de", "stuffing box temp de", "stuffing box out / dicharge out de")
    ),
    CanonicalParameterContract(
        10, "separator_in_temp_de", "Drive End Separator In Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "SEPARATOR_IN_TEMP_DE", "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("separator input temperature de", "separator in temp de", "separator in temperature de")
    ),
    CanonicalParameterContract(
        11, "separator_out_temp_de", "Drive End Separator Out Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "SEPARATOR_OUT_TEMP_DE", "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("separator output temperature de", "separator out temp de", "separator out temperature de")
    ),
    CanonicalParameterContract(
        12, "separator_return_temp_de", "Drive End Separator Return Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "SEPARATOR_RETURN_TEMP_DE", "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("separator return temperature de", "separator return temp de")
    ),
    CanonicalParameterContract(
        13, "cooler_surface_temp_de", "Drive End Cooler Surface Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "COOLER_SURFACE_TEMP_DE", "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("cooler surface temperature de", "cooler surface temp de")
    ),
    CanonicalParameterContract(
        14, "cooler_product_in_temp_de", "Drive End Cooler Product In Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "COOLER_PRODUCT_IN_TEMP_DE", "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("cooler product in temperature de", "cooler product in temp de")
    ),
    CanonicalParameterContract(
        15, "cooler_product_out_temp_de", "Drive End Cooler Product Out Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "COOLER_PRODUCT_OUT_TEMP_DE", "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("cooler product out temperature de", "cooler product out temp de")
    ),
    CanonicalParameterContract(
        16, "cooling_water_in_temp_de", "Drive End Cooler Water In Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "cooling_water_in_temp_de", None, "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("cooler water in temperature de", "cooling water in temp de", "cooler water in temp de")
    ),
    CanonicalParameterContract(
        17, "cooling_water_out_temp_de", "Drive End Cooler Water Out Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "cooling_water_out_temp_de", None, "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("cooler water out temperature de", "cooling water out temp de", "cooler water out temp de")
    ),
    CanonicalParameterContract(
        18, "buffer_in_temp_de", "Drive End Buffer In Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "BUFFER_IN_TEMP_DE", "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("buffer in temperature de", "buffer in temp de")
    ),
    CanonicalParameterContract(
        19, "buffer_out_temp_de", "Drive End Buffer Out Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "BUFFER_OUT_TEMP_DE", "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("buffer out temperature de", "buffer out temp de")
    ),
    CanonicalParameterContract(
        20, "reservoir_temp_de", "Drive End Reservoir Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "RESERVOIR_TEMP_DE", "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("reservoir temperature de", "reservoir temp de")
    ),
    CanonicalParameterContract(
        21, "reservoir_level_de", "Drive End Reservoir Level", "TEXT",
        StorageTier.CHILD_OBSERVATION_TABLE, "value_text", "RESERVOIR_LEVEL_DE", "DE",
        "STATUS", ("status", "text", "%", "cm", "level", ""),
        ("reservoir level de", "level reservoir de")
    ),
    CanonicalParameterContract(
        22, "reservoir_pressure_de", "Drive End Reservoir Pressure", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "quench_pressure_de", None, "DE",
        "kg/cm2", ("kg/cm2", "kg/cm", "bar", "barg"),
        ("reservoir pressure de", "quench pressure de", "tekanan reservoir de")
    ),
    CanonicalParameterContract(
        23, "temp_gauge_de", "Drive End Local Temperature Gauge", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "TEMP_GAUGE_DE", "DE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("temperature gauge de", "local temp gauge de", "local temperature gauge de", "temp gauge de")
    ),

    # --- NON-DRIVE END (NDE) (19 parameters) ---
    CanonicalParameterContract(
        24, "mechanical_seal_leak_nde", "Non-Drive End Mechanical Seal Leakage", "BOOLEAN",
        StorageTier.LEGACY_PARENT_TABLE, "mechanical_seal_leak_nde", None, "NDE",
        "NONE", ("none", "observed", "y/n", "boolean", ""),
        ("mechanical seal leakage nde", "mechseal leak nde", "seal leakage nde")
    ),
    CanonicalParameterContract(
        25, "seal_gland_temp_nde", "Non-Drive End Seal Gland Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "seal_gland_temp_nde", None, "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("seal gland temp nde", "seal gland temperature nde", "gland temp nde")
    ),
    CanonicalParameterContract(
        26, "flushing_in_temp_nde", "Non-Drive End Flush In Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "flushing_in_temp_nde", None, "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("flushing in temp nde", "flushing in temperature nde", "flushing temp nde")
    ),
    CanonicalParameterContract(
        27, "quench_temp_nde", "Non-Drive End Quench In Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "quench_temp_nde", None, "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("quench in temp nde", "quench in temperature nde", "quench temp nde", "quinch in temperature nde")
    ),
    CanonicalParameterContract(
        28, "stuffing_box_temp_nde", "Non-Drive End Stuffing Box Out Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "stuffing_box_temp_nde", None, "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("stuffing box out temp nde", "stuffing box out temperature nde", "stuffing box temp nde", "stuffing box out / dicharge out nde")
    ),
    CanonicalParameterContract(
        29, "separator_in_temp_nde", "Non-Drive End Separator In Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "SEPARATOR_IN_TEMP_NDE", "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("separator input temperature nde", "separator in temp nde", "separator in temperature nde")
    ),
    CanonicalParameterContract(
        30, "separator_out_temp_nde", "Non-Drive End Separator Out Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "SEPARATOR_OUT_TEMP_NDE", "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("separator output temperature nde", "separator out temp nde", "separator out temperature nde")
    ),
    CanonicalParameterContract(
        31, "separator_return_temp_nde", "Non-Drive End Separator Return Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "SEPARATOR_RETURN_TEMP_NDE", "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("separator return temperature nde", "separator return temp nde")
    ),
    CanonicalParameterContract(
        32, "cooler_surface_temp_nde", "Non-Drive End Cooler Surface Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "COOLER_SURFACE_TEMP_NDE", "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("cooler surface temperature nde", "cooler surface temp nde")
    ),
    CanonicalParameterContract(
        33, "cooler_product_in_temp_nde", "Non-Drive End Cooler Product In Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "COOLER_PRODUCT_IN_TEMP_NDE", "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("cooler product in temperature nde", "cooler product in temp nde")
    ),
    CanonicalParameterContract(
        34, "cooler_product_out_temp_nde", "Non-Drive End Cooler Product Out Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "COOLER_PRODUCT_OUT_TEMP_NDE", "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("cooler product out temperature nde", "cooler product out temp nde")
    ),
    CanonicalParameterContract(
        35, "cooling_water_in_temp_nde", "Non-Drive End Cooler Water In Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "cooling_water_in_temp_nde", None, "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("cooler water in temperature nde", "cooling water in temp nde", "cooler water in temp nde")
    ),
    CanonicalParameterContract(
        36, "cooling_water_out_temp_nde", "Non-Drive End Cooler Water Out Temperature", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "cooling_water_out_temp_nde", None, "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("cooler water out temperature nde", "cooling water out temp nde", "cooler water out temp nde")
    ),
    CanonicalParameterContract(
        37, "buffer_in_temp_nde", "Non-Drive End Buffer In Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "BUFFER_IN_TEMP_NDE", "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("buffer in temperature nde", "buffer in temp nde")
    ),
    CanonicalParameterContract(
        38, "buffer_out_temp_nde", "Non-Drive End Buffer Out Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "BUFFER_OUT_TEMP_NDE", "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("buffer out temperature nde", "buffer out temp nde")
    ),
    CanonicalParameterContract(
        39, "reservoir_temp_nde", "Non-Drive End Reservoir Temperature", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "RESERVOIR_TEMP_NDE", "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("reservoir temperature nde", "reservoir temp nde")
    ),
    CanonicalParameterContract(
        40, "reservoir_level_nde", "Non-Drive End Reservoir Level", "TEXT",
        StorageTier.CHILD_OBSERVATION_TABLE, "value_text", "RESERVOIR_LEVEL_NDE", "NDE",
        "STATUS", ("status", "text", "%", "cm", "level", ""),
        ("reservoir level nde", "level reservoir nde")
    ),
    CanonicalParameterContract(
        41, "reservoir_pressure_nde", "Non-Drive End Reservoir Pressure", "NUMERIC",
        StorageTier.LEGACY_PARENT_TABLE, "quench_pressure_nde", None, "NDE",
        "kg/cm2", ("kg/cm2", "kg/cm", "bar", "barg"),
        ("reservoir pressure nde", "quench pressure nde", "tekanan reservoir nde")
    ),
    CanonicalParameterContract(
        42, "temp_gauge_nde", "Non-Drive End Local Temperature Gauge", "NUMERIC",
        StorageTier.CHILD_MEASUREMENT_TABLE, "value_numeric", "TEMP_GAUGE_NDE", "NDE",
        "°C", ("°c", "c", "deg c", "celsius"),
        ("temperature gauge nde", "local temp gauge nde", "local temperature gauge nde", "temp gauge nde")
    ),
)

assert len(_PARAM_CONTRACTS) == 42, f"Expected 42 parameters, got {len(_PARAM_CONTRACTS)}"

_PARAM_BY_CODE: dict[str, CanonicalParameterContract] = {p.code: p for p in _PARAM_CONTRACTS}


def get_parameter_contract(code_or_alias: str) -> CanonicalParameterContract | None:
    """Finds canonical parameter contract by exact code or normalized alias."""
    if not code_or_alias:
        return None
    cleaned = code_or_alias.strip().lower()
    if cleaned in _PARAM_BY_CODE:
        return _PARAM_BY_CODE[cleaned]
    # Check aliases
    for p in _PARAM_CONTRACTS:
        if cleaned in p.aliases or cleaned == p.label.lower():
            return p
    return None


# ==============================================================================
# 3. ASSET RESOLVER & EXPLICIT APPROVED ALIASES
# ==============================================================================

# R5A.1 Authoritative explicit approved aliases:
# Key is (sheet_name, cell_col_or_position, source_literal) or (sheet_name, source_literal)
APPROVED_EXPLICIT_ALIASES: dict[tuple[str, str], str] = {
    ("H2P 701", "MM 51"): "701-MM-51",
    ("H2P 702", "MM 51"): "702-MM-51",
    ("AMINE", "2A"): "410-P-2A",
    ("AMINE", "2B"): "410-P-2B",
    ("AMINE", "3A"): "410-P-3A",
    ("AMINE", "3B"): "410-P-3B",
    ("AMINE", "1A"): "840-P-1A",
    ("AMINE", "1B"): "840-P-1B",
    ("AMINE", "2"): "840-P-2",
    # Note: 3A and 3B in AMINE unit 410 vs 840 are disambiguated by position/column or unit
    ("AMINE_840", "3A"): "840-P-3A",
    ("AMINE_840", "3B"): "840-P-3B",
    ("AMINE", "4A"): "840-P-4A",
    ("AMINE", "4B"): "840-P-4B",
    ("CDU II", "CP 201"): "101-CP-201",
    ("CDU II", "LRC 102"): "101-LRC-102",
}

# Explicit cell position mappings for AMINE to ensure zero ambiguity
APPROVED_CELL_ALIASES: dict[str, str] = {
    "H2P 701!M6": "701-MM-51",
    "H2P 702!O6": "702-MM-51",
    "AMINE!D6": "410-P-2A",
    "AMINE!E6": "410-P-2B",
    "AMINE!F6": "410-P-3A",
    "AMINE!G6": "410-P-3B",
    "AMINE!H6": "840-P-1A",
    "AMINE!I6": "840-P-1B",
    "AMINE!J6": "840-P-2",
    "AMINE!K6": "840-P-3A",
    "AMINE!L6": "840-P-3B",
    "AMINE!M6": "840-P-4A",
    "AMINE!N6": "840-P-4B",
    "CDU II!N6": "101-CP-201",
    "CDU II!O6": "101-LRC-102",
}

# The 5 quarantined source assets from Unit 946 (Oil Movement complex):
QUARANTINED_ASSET_LITERALS: frozenset[str] = frozenset({
    "946-P-2D",
    "946-P-4A",
    "946-P-4C",
    "946-P-8A",
    "946-P-8B",
})


@dataclass(frozen=True, slots=True)
class AssetResolutionResult:
    source_asset_literal: str
    canonical_asset_code: str | None
    resolution_method: str  # "EXACT_MATCH", "APPROVED_ALIAS", "UNRESOLVED"
    resolution_status: str  # "RESOLVED", "REVIEW_REQUIRED", "UNKNOWN_ASSET"
    persistence_eligible: bool
    notes: str


class AssetResolver:
    """Deterministic, policy-compliant asset resolver for CM field forms."""

    def __init__(self, registered_assets: Sequence[str] | None = None) -> None:
        self._registered_assets: frozenset[str] = frozenset(registered_assets or ())

    def resolve(
        self,
        source_literal: str,
        *,
        sheet_name: str | None = None,
        cell_position: str | None = None,
        effective_unit: str | None = None,
    ) -> AssetResolutionResult:
        lit = (source_literal or "").strip()
        if not lit:
            return AssetResolutionResult(
                source_asset_literal="",
                canonical_asset_code=None,
                resolution_method="UNRESOLVED",
                resolution_status=IngestionState.REVIEW_REQUIRED.value,
                persistence_eligible=False,
                notes="Blank source asset literal",
            )

        # 1. Exact canonical identity check
        if lit in self._registered_assets:
            return AssetResolutionResult(
                source_asset_literal=lit,
                canonical_asset_code=lit,
                resolution_method="EXACT_MATCH",
                resolution_status="RESOLVED",
                persistence_eligible=True,
                notes="Exact match against registered canonical assets",
            )

        # 2. Explicit approved alias lookup (by exact cell position)
        if cell_position and cell_position in APPROVED_CELL_ALIASES:
            canonical = APPROVED_CELL_ALIASES[cell_position]
            return AssetResolutionResult(
                source_asset_literal=lit,
                canonical_asset_code=canonical,
                resolution_method="APPROVED_ALIAS",
                resolution_status="RESOLVED",
                persistence_eligible=True,
                notes=f"Explicit approved alias for {cell_position}",
            )

        # 2b. Explicit approved alias lookup (by sheet + unit/tag)
        if sheet_name:
            sheet_key = (sheet_name, lit)
            if effective_unit == "840" and sheet_name == "AMINE":
                sheet_key = ("AMINE_840", lit)
            if sheet_key in APPROVED_EXPLICIT_ALIASES:
                canonical = APPROVED_EXPLICIT_ALIASES[sheet_key]
                return AssetResolutionResult(
                    source_asset_literal=lit,
                    canonical_asset_code=canonical,
                    resolution_method="APPROVED_ALIAS",
                    resolution_status="RESOLVED",
                    persistence_eligible=True,
                    notes=f"Explicit approved alias for sheet {sheet_name}",
                )

        # 3. Quarantined asset check (Unit 946 assets)
        constructed_candidate = f"{effective_unit}-P-{lit}" if effective_unit else lit
        if constructed_candidate in QUARANTINED_ASSET_LITERALS or lit in QUARANTINED_ASSET_LITERALS:
            return AssetResolutionResult(
                source_asset_literal=lit,
                canonical_asset_code=None,
                resolution_method="UNRESOLVED",
                resolution_status=IngestionState.REVIEW_REQUIRED.value,
                persistence_eligible=False,
                notes="Quarantined Unit 946 asset (NOT_IN_REGISTRY; requires Chief provisioning)",
            )

        # 4. Strictly reject generic regex or unauthorized aliases
        return AssetResolutionResult(
            source_asset_literal=lit,
            canonical_asset_code=None,
            resolution_method="UNRESOLVED",
            resolution_status=ErrorCode.UNKNOWN_ASSET.value,
            persistence_eligible=False,
            notes="No approved alias or exact match in asset registry (generic normalization prohibited)",
        )


# ==============================================================================
# 4. VALUE & STATE PARSER
# ==============================================================================

_NOT_APPLICABLE_TOKENS = frozenset({
    "N/A", "NA", "TIDAK ADA", "TIDAK BERLAKU", "NOT APPLICABLE", "T/A", "NONE_EQUIP"
})

_NOT_INSPECTED_TOKENS = frozenset({
    "NI", "NOT INSPECTED", "TIDAK DIPERIKSA", "BELUM DIPERIKSA", "OFF", "SHUTDOWN", "STANDBY", "STOP"
})

_LEAK_NONE_TOKENS = frozenset({
    "TIDAK BOCOR", "NO LEAK", "NONE", "AMAN", "TIDAK", "NORMAL", "0", "FALSE"
})

_LEAK_OBSERVED_TOKENS = frozenset({
    "BOCOR", "LEAK", "MENETES", "REMBS", "REMBES", "DRIP", "OBSERVED", "TRUE", "1"
})


@dataclass(frozen=True, slots=True)
class ParsedValue:
    raw_value: Any
    normalized_value: float | bool | str | None
    unit: str | None
    value_state: ValueState
    condition: ConditionState
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_field_value(
    raw: Any,
    contract: CanonicalParameterContract,
    *,
    unit: str | None = None,
    condition_raw: Any = None,
) -> ParsedValue:
    """Parses raw cell value into validated ParsedValue conforming to R5A invariants:

    - 0 != N/A
    - N/A != NOT_INSPECTED
    - UNKNOWN != NOT_INSPECTED
    - blank != 0
    - blank does not silently become 0, N/A, or NORMAL.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # Condition state parsing
    condition = _parse_condition_state(condition_raw)

    # 1. Blank / None handling
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return ParsedValue(
            raw_value=raw,
            normalized_value=None,
            unit=unit or contract.canonical_unit,
            value_state=ValueState.NOT_INSPECTED,
            condition=condition if condition != ConditionState.UNKNOWN else ConditionState.NOT_INSPECTED,
            warnings=warnings,
            errors=errors,
        )

    # String normalization for token matching
    raw_str = str(raw).strip().upper()

    # 2. NOT_APPLICABLE check
    if raw_str in _NOT_APPLICABLE_TOKENS:
        return ParsedValue(
            raw_value=raw,
            normalized_value=None,
            unit=unit or contract.canonical_unit,
            value_state=ValueState.NOT_APPLICABLE,
            condition=ConditionState.NOT_APPLICABLE,
            warnings=warnings,
            errors=errors,
        )

    # 3. NOT_INSPECTED check
    if raw_str in _NOT_INSPECTED_TOKENS:
        return ParsedValue(
            raw_value=raw,
            normalized_value=None,
            unit=unit or contract.canonical_unit,
            value_state=ValueState.NOT_INSPECTED,
            condition=ConditionState.NOT_INSPECTED,
            warnings=warnings,
            errors=errors,
        )

    # 4. Unit validation (if provided)
    clean_unit = (unit or contract.canonical_unit).strip().lower()
    if contract.allowed_units and clean_unit not in contract.allowed_units:
        warnings.append(f"Unit '{unit}' not in expected allowed units {contract.allowed_units}")

    # 5. Type-specific parsing
    if contract.data_type == "BOOLEAN":
        # Leakage parameter (NONE vs OBSERVED)
        if raw is False or raw_str in _LEAK_NONE_TOKENS:
            return ParsedValue(
                raw_value=raw,
                normalized_value=False,
                unit="NONE",
                value_state=ValueState.VALUE_PRESENT,
                condition=condition if condition != ConditionState.UNKNOWN else ConditionState.NORMAL,
                warnings=warnings,
                errors=errors,
            )
        elif raw is True or raw_str in _LEAK_OBSERVED_TOKENS:
            # OBSERVED leakage: flagged ABNORMAL condition, but NEVER creates ltsa_finding automatically
            return ParsedValue(
                raw_value=raw,
                normalized_value=True,
                unit="NONE",
                value_state=ValueState.VALUE_PRESENT,
                condition=ConditionState.ABNORMAL,
                warnings=warnings,
                errors=errors,
            )
        else:
            errors.append(f"Invalid boolean/leakage token: '{raw}'")
            return ParsedValue(
                raw_value=raw,
                normalized_value=None,
                unit="NONE",
                value_state=ValueState.UNKNOWN,
                condition=ConditionState.UNKNOWN,
                warnings=warnings,
                errors=errors,
            )

    elif contract.data_type == "NUMERIC":
        # Strictly numeric parameters
        try:
            val_float = float(raw)
            # Differentiate 0.0 from blank or N/A
            return ParsedValue(
                raw_value=raw,
                normalized_value=val_float,
                unit=unit or contract.canonical_unit,
                value_state=ValueState.VALUE_PRESENT,
                condition=condition if condition != ConditionState.UNKNOWN else ConditionState.NORMAL,
                warnings=warnings,
                errors=errors,
            )
        except (ValueError, TypeError):
            errors.append(f"Invalid numeric value '{raw}' for {contract.code}")
            return ParsedValue(
                raw_value=raw,
                normalized_value=None,
                unit=unit or contract.canonical_unit,
                value_state=ValueState.UNKNOWN,
                condition=ConditionState.UNKNOWN,
                warnings=warnings,
                errors=errors,
            )

    elif contract.data_type == "TEXT":
        # Observation parameter (e.g. reservoir level)
        return ParsedValue(
            raw_value=raw,
            normalized_value=str(raw).strip(),
            unit=unit or contract.canonical_unit,
            value_state=ValueState.VALUE_PRESENT,
            condition=condition if condition != ConditionState.UNKNOWN else ConditionState.NORMAL,
            warnings=warnings,
            errors=errors,
        )

    # Fallback
    return ParsedValue(
        raw_value=raw,
        normalized_value=str(raw),
        unit=unit or contract.canonical_unit,
        value_state=ValueState.VALUE_PRESENT,
        condition=condition,
        warnings=warnings,
        errors=errors,
    )


def _parse_condition_state(cond: Any) -> ConditionState:
    if cond is None or cond == "":
        return ConditionState.UNKNOWN
    val = str(cond).strip().upper()
    if val in ("NORMAL", "NORM", "OK", "BAIK", "GREEN"):
        return ConditionState.NORMAL
    if val in ("MONITOR", "MON", "WATCH", "YELLOW"):
        return ConditionState.MONITOR
    if val in ("ABNORMAL", "ABN", "CRITICAL", "ALARM", "RED"):
        return ConditionState.ABNORMAL
    if val in _NOT_APPLICABLE_TOKENS:
        return ConditionState.NOT_APPLICABLE
    if val in _NOT_INSPECTED_TOKENS:
        return ConditionState.NOT_INSPECTED
    return ConditionState.UNKNOWN


# ==============================================================================
# 5. STORAGE PLANNING & DOUBLE-PERSISTENCE PREVENTION
# ==============================================================================

@dataclass(frozen=True, slots=True)
class AssetStoragePlan:
    """Explicit mapping plan for an asset's 42 canonical parameters:

    - 20 Legacy parent columns in condition_monitoring_reading
    - 20 Child measurements in condition_monitoring_reading_measurement
    - 2 Child observations in condition_monitoring_reading_measurement
    """
    asset_code: str
    legacy_parent_values: dict[str, Any]
    child_measurements: list[dict[str, Any]]
    child_observations: list[dict[str, Any]]


def plan_asset_storage(
    asset_code: str,
    parsed_items: dict[str, ParsedValue],
) -> AssetStoragePlan:
    """Deterministically routes 42 parsed values to their exclusive storage tier."""
    legacy_vals: dict[str, Any] = {}
    child_meas: list[dict[str, Any]] = []
    child_obs: list[dict[str, Any]] = []

    for contract in _PARAM_CONTRACTS:
        parsed = parsed_items.get(contract.code)
        if not parsed or parsed.value_state != ValueState.VALUE_PRESENT:
            continue

        if contract.storage_tier == StorageTier.LEGACY_PARENT_TABLE:
            # Enforce single column write
            legacy_vals[contract.target_column] = parsed.normalized_value

        elif contract.storage_tier == StorageTier.CHILD_MEASUREMENT_TABLE:
            child_meas.append({
                "measurement_code": contract.measurement_code_if_child,
                "measurement_label": contract.label,
                "value_numeric": parsed.normalized_value,
                "value_text": None,
                "unit": parsed.unit or contract.canonical_unit,
                "measurement_side": contract.measurement_side,
                "source_label": contract.code,
            })

        elif contract.storage_tier == StorageTier.CHILD_OBSERVATION_TABLE:
            child_obs.append({
                "measurement_code": contract.measurement_code_if_child,
                "measurement_label": contract.label,
                "value_numeric": None,
                "value_text": str(parsed.normalized_value),
                "unit": parsed.unit or contract.canonical_unit,
                "measurement_side": contract.measurement_side,
                "source_label": contract.code,
            })

    return AssetStoragePlan(
        asset_code=asset_code,
        legacy_parent_values=legacy_vals,
        child_measurements=child_meas,
        child_observations=child_obs,
    )


# ==============================================================================
# 6. IDEMPOTENCY & PROVENANCE
# ==============================================================================

def generate_idempotency_key(
    *,
    source_sheet: str,
    asset_identifier: str,
    reading_date: str,
    parameter_payload: Sequence[tuple[str, Any]],
) -> str:
    """Computes stable, deterministic idempotency signature."""
    sorted_payload = sorted(parameter_payload, key=lambda x: x[0])
    raw_sig = f"{source_sheet}::{asset_identifier}::{reading_date}::{sorted_payload}"
    digest = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()[:12].upper()
    return f"FF-CMON::{source_sheet}::{asset_identifier}::{reading_date}::{digest}"


# ==============================================================================
# 7. WALKING ROUND BATCH & PREVIEW MODEL
# ==============================================================================

@dataclass
class ParameterPreviewItem:
    canonical_code: str
    source_label: str
    raw_value: Any
    normalized_value: Any
    unit: str
    value_state: str
    condition: str
    storage_target: str
    warnings: list[str]
    errors: list[str]


@dataclass
class AssetReadingPreview:
    source_asset: str
    canonical_asset: str | None
    asset_resolution: str
    resolution_status: str
    persistence_eligible: bool
    reading_date: str
    items: list[ParameterPreviewItem]
    storage_plan: AssetStoragePlan | None
    warnings: list[str]
    errors: list[str]
    ingestion_status: str
    idempotency_key: str


@dataclass
class WalkingRoundBatchPreview:
    source_workbook: str
    source_sheet: str
    reading_date: str
    total_assets: int
    resolvable_assets: int
    quarantined_assets: int
    asset_previews: list[AssetReadingPreview]


class ConditionMonitoringFieldFormEngine:
    """Local Condition Monitoring field-form ingestion engine (CM R5B)."""

    def __init__(self, registered_assets: Sequence[str] | None = None) -> None:
        self._resolver = AssetResolver(registered_assets)

    def preview_batch(
        self,
        *,
        source_workbook: str,
        source_sheet: str,
        reading_date: str,
        asset_columns: list[dict[str, Any]],
    ) -> WalkingRoundBatchPreview:
        """Pure in-memory preview of a walking round sheet batch.

        Does NOT write to database.
        Quarantined assets receive REVIEW_REQUIRED and persistence_eligible=False.
        """
        asset_previews: list[AssetReadingPreview] = []
        resolvable = 0
        quarantined = 0

        for col in asset_columns:
            source_tag = col.get("source_tag", "")
            cell_pos = col.get("cell_position", "")
            eff_unit = col.get("effective_unit", "")
            raw_measurements = col.get("measurements", {})

            # 1. Resolve asset
            res = self._resolver.resolve(
                source_tag,
                sheet_name=source_sheet,
                cell_position=cell_pos,
                effective_unit=eff_unit,
            )

            if res.persistence_eligible:
                resolvable += 1
            else:
                quarantined += 1

            # 2. Parse all 42 parameters
            preview_items: list[ParameterPreviewItem] = []
            parsed_dict: dict[str, ParsedValue] = {}
            asset_warnings: list[str] = []
            asset_errors: list[str] = []

            if not res.persistence_eligible:
                asset_warnings.append(res.notes)

            payload_tuples: list[tuple[str, Any]] = []

            for contract in _PARAM_CONTRACTS:
                raw_cell = raw_measurements.get(contract.code)
                parsed = parse_field_value(raw_cell, contract)
                parsed_dict[contract.code] = parsed
                payload_tuples.append((contract.code, parsed.normalized_value))

                target_descr = (
                    f"Parent Col: {contract.target_column}"
                    if contract.storage_tier == StorageTier.LEGACY_PARENT_TABLE
                    else f"Child: {contract.measurement_code_if_child} ({contract.measurement_side})"
                )

                if parsed.errors:
                    asset_errors.extend(parsed.errors)
                if parsed.warnings:
                    asset_warnings.extend(parsed.warnings)

                preview_items.append(ParameterPreviewItem(
                    canonical_code=contract.code,
                    source_label=contract.label,
                    raw_value=parsed.raw_value,
                    normalized_value=parsed.normalized_value,
                    unit=parsed.unit or contract.canonical_unit,
                    value_state=parsed.value_state.value,
                    condition=parsed.condition.value,
                    storage_target=target_descr,
                    warnings=parsed.warnings,
                    errors=parsed.errors,
                ))

            # 3. Storage plan (only if resolvable)
            storage_plan = (
                plan_asset_storage(res.canonical_asset_code, parsed_dict)
                if res.canonical_asset_code
                else None
            )

            # 4. Status
            if not res.persistence_eligible:
                status = IngestionState.REVIEW_REQUIRED.value
            elif asset_errors:
                status = IngestionState.REVIEW_REQUIRED.value
            else:
                status = IngestionState.READY_TO_APPLY.value

            # 5. Idempotency key
            idempotency_key = generate_idempotency_key(
                source_sheet=source_sheet,
                asset_identifier=res.canonical_asset_code or source_tag,
                reading_date=reading_date,
                parameter_payload=payload_tuples,
            )

            asset_previews.append(AssetReadingPreview(
                source_asset=source_tag,
                canonical_asset=res.canonical_asset_code,
                asset_resolution=res.resolution_method,
                resolution_status=res.resolution_status,
                persistence_eligible=res.persistence_eligible,
                reading_date=reading_date,
                items=preview_items,
                storage_plan=storage_plan,
                warnings=asset_warnings,
                errors=asset_errors,
                ingestion_status=status,
                idempotency_key=idempotency_key,
            ))

        return WalkingRoundBatchPreview(
            source_workbook=source_workbook,
            source_sheet=source_sheet,
            reading_date=reading_date,
            total_assets=len(asset_columns),
            resolvable_assets=resolvable,
            quarantined_assets=quarantined,
            asset_previews=asset_previews,
        )


# ==============================================================================
# 8. ATOMIC PERSISTENCE ADAPTER (DRY-RUN / TEST HARNESS)
# ==============================================================================

class QuarantinedAssetPersistenceError(Exception):
    """Attempted to persist a quarantined or unresolved asset."""


class AssetPersistenceTransactionError(Exception):
    """Failure during atomic multi-table asset persistence."""


class FieldFormPersistenceAdapter:
    """Atomic per-asset persistence boundary adapter.

    Enforces all-or-nothing atomicity between parent condition_monitoring_reading
    and child condition_monitoring_reading_measurement rows.
    Hard invariant: Never automatically creates ltsa_finding.
    """

    def build_atomic_sql_transaction(
        self,
        preview: AssetReadingPreview,
        *,
        created_by: str,
        source_reference: str,
    ) -> str:
        """Builds a single atomic SQL transaction script."""
        if not preview.persistence_eligible or not preview.storage_plan:
            raise QuarantinedAssetPersistenceError(
                f"Asset '{preview.source_asset}' is not eligible for persistence (status: {preview.resolution_status})"
            )

        plan = preview.storage_plan
        reading_code = f"CMONR-{uuid.uuid4().hex[:12].upper()}"

        # 1. Build parent insert
        parent_cols = ["condition_monitoring_reading_code", "asset_code", "reading_date",
                       "workflow_status", "provenance", "source_reference", "created_by", "updated_by"]
        parent_vals = [_sql(reading_code), _sql(plan.asset_code), _sql(preview.reading_date),
                       _sql("DRAFT"), _sql("FIELD_FORM"), _sql(source_reference), _sql(created_by), _sql(created_by)]

        for col, val in plan.legacy_parent_values.items():
            parent_cols.append(col)
            parent_vals.append(_sql(val))

        sql_parent = (
            f"INSERT INTO condition_monitoring_reading ({', '.join(parent_cols)}) "
            f"VALUES ({', '.join(parent_vals)});"
        )

        # 2. Build child measurements insert
        child_sqls: list[str] = []
        for m in plan.child_measurements + plan.child_observations:
            child_sqls.append(
                "INSERT INTO condition_monitoring_reading_measurement "
                "(reading_id, measurement_code, measurement_label, value_numeric, value_text, "
                "unit, measurement_side, source_label, verification_status, created_by, updated_by) "
                f"VALUES ({_sql(reading_code)}, {_sql(m['measurement_code'])}, {_sql(m['measurement_label'])}, "
                f"{_sql(m['value_numeric'])}, {_sql(m['value_text'])}, {_sql(m['unit'])}, "
                f"{_sql(m['measurement_side'])}, {_sql(m['source_label'])}, 'DRAFT', {_sql(created_by)}, {_sql(created_by)});"
            )

        # Combine inside explicit transaction
        script = [
            "BEGIN;",
            f"-- Asset Precheck: ensure {plan.asset_code} exists",
            f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM asset_registry WHERE asset_code = {_sql(plan.asset_code)}) "
            f"THEN RAISE EXCEPTION 'Asset % not registered', {_sql(plan.asset_code)}; END IF; END $$;",
            sql_parent,
        ]
        script.extend(child_sqls)
        script.append("COMMIT;")

        return "\n".join(script)

    def apply_dry_run(
        self,
        preview: AssetReadingPreview,
        *,
        created_by: str,
    ) -> dict[str, Any]:
        """Validates the transaction plan without mutating the database."""
        sql = self.build_atomic_sql_transaction(
            preview,
            created_by=created_by,
            source_reference=preview.idempotency_key,
        )
        return {
            "success": True,
            "dry_run": True,
            "asset_code": preview.canonical_asset,
            "parent_table": "condition_monitoring_reading",
            "child_count": (
                len(preview.storage_plan.child_measurements) +
                len(preview.storage_plan.child_observations)
            ) if preview.storage_plan else 0,
            "sql_preview": sql,
            "findings_created": 0,  # Hard guarantee: findings never auto-created
        }


__all__ = [
    "IngestionState",
    "ValueState",
    "ConditionState",
    "LeakageState",
    "StorageTier",
    "ErrorCode",
    "CanonicalParameterContract",
    "get_parameter_contract",
    "AssetResolutionResult",
    "AssetResolver",
    "ParsedValue",
    "parse_field_value",
    "AssetStoragePlan",
    "plan_asset_storage",
    "generate_idempotency_key",
    "ParameterPreviewItem",
    "AssetReadingPreview",
    "WalkingRoundBatchPreview",
    "ConditionMonitoringFieldFormEngine",
    "QuarantinedAssetPersistenceError",
    "AssetPersistenceTransactionError",
    "FieldFormPersistenceAdapter",
    "APPROVED_EXPLICIT_ALIASES",
    "APPROVED_CELL_ALIASES",
    "QUARANTINED_ASSET_LITERALS",
]

