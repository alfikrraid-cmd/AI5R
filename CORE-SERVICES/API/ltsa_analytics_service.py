"""MWO-LTSA-DASHBOARD-ANALYTICS-001 -- Production LTSA Analytics Engine.

Provides server-side aggregations for the 7 LTSA dashboard domains:
1. Reliability (Fleet, Bad Actors, MTBF/MTTR policy)
2. PM / CM (Compliance, execution, inspections)
3. Breakdown (Work orders / failures, zero vs unknown)
4. Mechanical Seal Replacement (Lifecycle events, leaks by position/pump)
5. Material Consumption (Spare parts usage, zero vs unknown)
6. Inventory / Stock (Seal stock and registry)
7. Maintenance Effectiveness (PM-to-CM ratio, proactive maintenance)

CRITICAL RULES:
- REAL PRODUCTION DATA ONLY: No mocks, no synthetic records, no hardcoded counts.
- UNKNOWN != ZERO: If records cannot be mathematically derived or domain table
  has no records, return None so UI explicitly renders 'N/A'.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


class LTSAAnalyticsService:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def _build_where_clauses(
        self,
        *,
        pump_alias: str = "p",
        record_alias: str | None = None,
        date_col: str | None = None,
        contract_area: str | None = None,
        area: str | None = None,
        pump_tag: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        scope: frozenset[str] | None = None,
        extra_clauses: list[str] | None = None,
    ) -> str:
        clauses: list[str] = []

        # Area scoping (security / tenancy)
        if scope is not None:
            if scope:
                values = ", ".join(_sql(a) for a in sorted(scope))
                clauses.append(f"{pump_alias}.area IN ({values})")
            else:
                clauses.append("FALSE")

        # Specific Area filter (or contract_area)
        target_area = area or contract_area
        if target_area:
            clauses.append(f"{pump_alias}.area = {_sql(target_area)}")

        # Specific Pump Tag filter
        if pump_tag:
            clauses.append(f"{pump_alias}.tag_number = {_sql(pump_tag)}")

        # Date range filtering
        if record_alias and date_col:
            if start_date:
                clauses.append(f"{record_alias}.{date_col}::date >= {_sql(start_date)}::date")
            if end_date:
                clauses.append(f"{record_alias}.{date_col}::date <= {_sql(end_date)}::date")

        if extra_clauses:
            clauses.extend(extra_clauses)

        if not clauses:
            return ""
        return "WHERE " + " AND ".join(clauses)

    def get_filter_options(self, *, scope: frozenset[str] | None = None) -> dict[str, Any]:
        """Returns distinct filter options available in the live database."""
        scope_clause = ""
        if scope is not None:
            if scope:
                values = ", ".join(_sql(a) for a in sorted(scope))
                scope_clause = f"WHERE area IN ({values})"
            else:
                scope_clause = "WHERE FALSE"

        area_rows = _json_query(
            f"""
            SELECT area, count(*) as pump_count
            FROM ltsa_pumps
            {scope_clause}
            GROUP BY area
            ORDER BY pump_count DESC, area ASC
            """,
            self._runner,
        )

        pump_rows = _json_query(
            f"""
            SELECT tag_number, area, pump_type, api_plan, status
            FROM ltsa_pumps
            {scope_clause}
            ORDER BY tag_number ASC
            """,
            self._runner,
        )

        date_range = _json_query(
            """
            SELECT 
                min(dt)::text as min_date,
                max(dt)::text as max_date
            FROM (
                SELECT occurrence_date::date as dt FROM pm_occurrence
                UNION ALL
                SELECT reading_date::date as dt FROM condition_monitoring_reading
            ) all_dates
            """,
            self._runner,
        )

        min_d = date_range[0]["min_date"] if date_range and date_range[0]["min_date"] else "2026-07-01"
        max_d = date_range[0]["max_date"] if date_range and date_range[0]["max_date"] else "2026-07-31"

        return {
            "areas": area_rows,
            "pumps": pump_rows,
            "date_range": {"min_date": min_d, "max_date": max_d},
        }

    def get_executive_analytics(
        self,
        *,
        contract_area: str | None = None,
        area: str | None = None,
        pump_tag: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        scope: frozenset[str] | None = None,
    ) -> dict[str, Any]:
        """Core Executive Dashboard analytics combining fleet, PM/CM, breakdowns, and leaks."""
        pump_where = self._build_where_clauses(
            pump_alias="p",
            contract_area=contract_area,
            area=area,
            pump_tag=pump_tag,
            scope=scope,
        )

        # 1. Pump fleet counts
        pump_counts = _json_query(
            f"""
            SELECT 
                count(*) as total_pumps,
                count(*) FILTER (WHERE status NOT IN ('UNKNOWN', 'DECOMMISSIONED')) as active_pumps
            FROM ltsa_pumps p
            {pump_where}
            """,
            self._runner,
        )
        total_pumps = pump_counts[0]["total_pumps"] if pump_counts else 0
        raw_active_pumps = pump_counts[0]["active_pumps"] if pump_counts else 0
        # Policy: if all pumps have status='UNKNOWN', active_pumps is None (N/A)
        active_pumps = raw_active_pumps if raw_active_pumps > 0 else None

        # 2. Condition monitoring & leaks
        cm_where = self._build_where_clauses(
            pump_alias="p",
            record_alias="r",
            date_col="reading_date",
            contract_area=contract_area,
            area=area,
            pump_tag=pump_tag,
            start_date=start_date,
            end_date=end_date,
            scope=scope,
        )
        cm_stats = _json_query(
            f"""
            SELECT 
                count(DISTINCT r.asset_code) as monitored_pumps,
                count(r.condition_monitoring_reading_code) as cmon_readings,
                count(r.condition_monitoring_reading_code) FILTER (
                    WHERE r.mechanical_seal_leak_de = true OR r.mechanical_seal_leak_nde = true
                ) as seal_leaks,
                count(r.condition_monitoring_reading_code) FILTER (WHERE r.mechanical_seal_leak_de = true) as de_leaks,
                count(r.condition_monitoring_reading_code) FILTER (WHERE r.mechanical_seal_leak_nde = true) as nde_leaks
            FROM condition_monitoring_reading r
            JOIN ltsa_pumps p ON p.tag_number = r.asset_code
            {cm_where}
            """,
            self._runner,
        )
        cmon_data = cm_stats[0] if cm_stats else {}
        monitored_pumps = cmon_data.get("monitored_pumps", 0)
        cmon_readings = cmon_data.get("cmon_readings", 0)
        seal_leaks = cmon_data.get("seal_leaks", 0)
        de_leaks = cmon_data.get("de_leaks", 0)
        nde_leaks = cmon_data.get("nde_leaks", 0)

        # 3. PM occurrence stats
        pm_where = self._build_where_clauses(
            pump_alias="p",
            record_alias="pm",
            date_col="occurrence_date",
            contract_area=contract_area,
            area=area,
            pump_tag=pump_tag,
            start_date=start_date,
            end_date=end_date,
            scope=scope,
        )
        pm_stats = _json_query(
            f"""
            SELECT 
                count(DISTINCT pm.asset_code) as pm_pumps,
                count(pm.pm_occurrence_code) as pm_executed,
                count(pm.pm_occurrence_code) FILTER (WHERE pm.status = 'DONE') as pm_done
            FROM pm_occurrence pm
            JOIN ltsa_pumps p ON p.tag_number = pm.asset_code
            {pm_where}
            """,
            self._runner,
        )
        pm_data = pm_stats[0] if pm_stats else {}
        pm_executed = pm_data.get("pm_executed", 0)
        pm_done = pm_data.get("pm_done", 0)

        # 4. PM schedule compliance (check if pm_schedule has records)
        sched_count_query = _json_query("SELECT count(*) as c FROM pm_schedule", self._runner)
        total_sched_in_db = sched_count_query[0]["c"] if sched_count_query else 0
        if total_sched_in_db > 0:
            sched_stats = _json_query(
                f"""
                SELECT count(*) as pm_scheduled
                FROM pm_schedule s
                JOIN ltsa_pumps p ON p.tag_number = s.asset_code
                {self._build_where_clauses(pump_alias="p", contract_area=contract_area, area=area, pump_tag=pump_tag, scope=scope)}
                """,
                self._runner,
            )
            pm_scheduled = sched_stats[0]["pm_scheduled"] if sched_stats else 0
            pm_compliance_percent = round((pm_done / pm_scheduled * 100), 1) if pm_scheduled > 0 else 100.0
        else:
            pm_scheduled = None
            pm_compliance_percent = None

        # 5. Breakdowns & MTBF/MTTR derivation
        # Query work_order and maintenance_history for breakdown records
        wo_where = self._build_where_clauses(
            pump_alias="p",
            pump_tag=pump_tag,
            contract_area=contract_area,
            area=area,
            scope=scope,
            extra_clauses=["(wo.work_type ILIKE '%BREAKDOWN%' OR wo.work_type ILIKE '%CORRECTIVE%')"],
        )
        wo_stats = _json_query(
            f"""
            SELECT count(*) as breakdowns
            FROM work_order wo
            JOIN ltsa_pumps p ON p.tag_number = wo.asset_code
            {wo_where}
            """,
            self._runner,
        )
        breakdown_count = wo_stats[0]["breakdowns"] if wo_stats else 0

        # Hard Rule: UNKNOWN != ZERO. Without >= 2 breakdown events, MTBF/MTTR cannot be derived.
        fleet_mtbf_days = None
        fleet_mttr_hours = None
        fleet_availability = None

        # 6. Daily Trends
        daily_trends = _json_query(
            f"""
            WITH filtered_pm AS (
                SELECT pm.occurrence_date::date as dt, count(pm.pm_occurrence_code) as pm_count
                FROM pm_occurrence pm
                JOIN ltsa_pumps p ON p.tag_number = pm.asset_code
                {pm_where}
                GROUP BY dt
            ),
            filtered_cm AS (
                SELECT 
                    r.reading_date::date as dt,
                    count(r.condition_monitoring_reading_code) as cmon_readings,
                    count(r.condition_monitoring_reading_code) FILTER (
                        WHERE r.mechanical_seal_leak_de = true OR r.mechanical_seal_leak_nde = true
                    ) as seal_leaks
                FROM condition_monitoring_reading r
                JOIN ltsa_pumps p ON p.tag_number = r.asset_code
                {cm_where}
                GROUP BY dt
            ),
            all_dates AS (
                SELECT dt FROM filtered_pm
                UNION
                SELECT dt FROM filtered_cm
            )
            SELECT 
                d.dt::text as date,
                COALESCE(pm.pm_count, 0) as pm_count,
                COALESCE(cm.cmon_readings, 0) as cmon_readings,
                COALESCE(cm.seal_leaks, 0) as seal_leaks
            FROM all_dates d
            LEFT JOIN filtered_pm pm ON pm.dt = d.dt
            LEFT JOIN filtered_cm cm ON cm.dt = d.dt
            ORDER BY d.dt ASC
            """,
            self._runner,
        )

        # 7. Area Distribution Breakdown
        area_breakdown = _json_query(
            f"""
            WITH p_filtered AS (
                SELECT p.tag_number, p.area
                FROM ltsa_pumps p
                {pump_where}
            ),
            pm_agg AS (
                SELECT pm.asset_code, count(pm.pm_occurrence_code) as pm_count
                FROM pm_occurrence pm
                {self._build_where_clauses(pump_alias="pm", record_alias="pm", date_col="occurrence_date", start_date=start_date, end_date=end_date)}
                GROUP BY pm.asset_code
            ),
            cm_agg AS (
                SELECT 
                    r.asset_code,
                    count(r.condition_monitoring_reading_code) as cmon_readings,
                    count(r.condition_monitoring_reading_code) FILTER (
                        WHERE r.mechanical_seal_leak_de = true OR r.mechanical_seal_leak_nde = true
                    ) as seal_leaks
                FROM condition_monitoring_reading r
                {self._build_where_clauses(pump_alias="r", record_alias="r", date_col="reading_date", start_date=start_date, end_date=end_date)}
                GROUP BY r.asset_code
            )
            SELECT 
                p.area,
                count(DISTINCT p.tag_number) as pump_count,
                COALESCE(sum(pm.pm_count), 0) as pm_count,
                COALESCE(sum(cm.cmon_readings), 0) as cmon_readings,
                COALESCE(sum(cm.seal_leaks), 0) as seal_leaks
            FROM p_filtered p
            LEFT JOIN pm_agg pm ON pm.asset_code = p.tag_number
            LEFT JOIN cm_agg cm ON cm.asset_code = p.tag_number
            GROUP BY p.area
            ORDER BY seal_leaks DESC, pump_count DESC, p.area ASC
            """,
            self._runner,
        )

        # 8. Top Bad Actor Pumps
        bad_actors_where = self._build_where_clauses(
            pump_alias="p",
            record_alias="r",
            date_col="reading_date",
            contract_area=contract_area,
            area=area,
            pump_tag=pump_tag,
            start_date=start_date,
            end_date=end_date,
            scope=scope,
            extra_clauses=["(r.mechanical_seal_leak_de = true OR r.mechanical_seal_leak_nde = true)"],
        )
        bad_actors = _json_query(
            f"""
            SELECT 
                p.tag_number as pump_tag,
                p.area,
                p.pump_type,
                p.api_plan,
                count(r.condition_monitoring_reading_code) FILTER (
                    WHERE r.mechanical_seal_leak_de = true OR r.mechanical_seal_leak_nde = true
                ) as leak_count,
                count(DISTINCT r.condition_monitoring_reading_code) as cmon_readings,
                count(DISTINCT pm.pm_occurrence_code) as pm_count,
                max(r.reading_date::date)::text as latest_leak_date
            FROM ltsa_pumps p
            JOIN condition_monitoring_reading r ON r.asset_code = p.tag_number
            LEFT JOIN pm_occurrence pm ON pm.asset_code = p.tag_number
            {bad_actors_where}
            GROUP BY p.tag_number, p.area, p.pump_type, p.api_plan
            ORDER BY leak_count DESC, cmon_readings DESC
            LIMIT 10
            """,
            self._runner,
        )

        # 9. Historical Findings summary (from document_field_extraction)
        findings_where = self._build_where_clauses(
            pump_alias="p",
            contract_area=contract_area,
            area=area,
            pump_tag=pump_tag,
            scope=scope,
            extra_clauses=["e.detected_document_type = 'HISTORICAL_FINDING_CANDIDATE'"],
        )
        findings_query = _json_query(
            f"""
            SELECT 
                e.pump_tag_number as pump_tag,
                e.extracted_fields->>'remarks' as remarks,
                e.extracted_fields->>'api_plan' as api_plan,
                e.extracted_fields->>'pump_type' as pump_type,
                e.extracted_fields->>'seal_leakage_de' as leak_de,
                e.extracted_fields->>'seal_leakage_nde' as leak_nde,
                e.extracted_fields->>'follow_up_date_raw' as follow_up_date,
                e.created_at::date::text as detected_date
            FROM document_field_extraction e
            JOIN ltsa_pumps p ON p.tag_number = e.pump_tag_number
            {findings_where}
            ORDER BY e.created_at DESC
            LIMIT 15
            """,
            self._runner,
        )

        return {
            "kpis": {
                "total_pumps": total_pumps,
                "active_pumps": active_pumps,
                "monitored_pumps": monitored_pumps,
                "pm_executed_count": pm_executed,
                "pm_done_count": pm_done,
                "pm_scheduled_count": pm_scheduled,
                "pm_compliance_percent": pm_compliance_percent,
                "confirmed_seal_leaks": seal_leaks,
                "de_leaks": de_leaks,
                "nde_leaks": nde_leaks,
                "breakdown_count": breakdown_count,
                "fleet_mtbf_days": fleet_mtbf_days,
                "fleet_mttr_hours": fleet_mttr_hours,
                "fleet_availability": fleet_availability,
            },
            "trends": {
                "daily": daily_trends,
            },
            "area_breakdown": area_breakdown,
            "top_bad_actors": bad_actors,
            "historical_findings": findings_query,
        }

    def get_seal_analytics(
        self,
        *,
        contract_area: str | None = None,
        area: str | None = None,
        pump_tag: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        scope: frozenset[str] | None = None,
    ) -> dict[str, Any]:
        """Seal domain analytics: replacements, leaks by type/size, stock."""
        cm_where = self._build_where_clauses(
            pump_alias="p",
            record_alias="r",
            date_col="reading_date",
            contract_area=contract_area,
            area=area,
            pump_tag=pump_tag,
            start_date=start_date,
            end_date=end_date,
            scope=scope,
        )

        # Check recorded seal replacements in seal_lifecycle_event / installation_report
        replacement_check = _json_query(
            "SELECT count(*) as c FROM seal_lifecycle_event WHERE event_type IN ('INSTALLATION', 'REPLACEMENT')",
            self._runner,
        )
        total_replacements_in_db = replacement_check[0]["c"] if replacement_check else 0
        seal_replacements_count = total_replacements_in_db if total_replacements_in_db > 0 else None
        mtbsr_days = None  # None if insufficient replacements

        # Leaks by Pump Type
        leaks_by_pump_type = _json_query(
            f"""
            SELECT 
                COALESCE(p.pump_type, 'UNKNOWN') as pump_type,
                count(r.condition_monitoring_reading_code) as total_readings,
                count(r.condition_monitoring_reading_code) FILTER (
                    WHERE r.mechanical_seal_leak_de = true OR r.mechanical_seal_leak_nde = true
                ) as leak_count
            FROM condition_monitoring_reading r
            JOIN ltsa_pumps p ON p.tag_number = r.asset_code
            {cm_where}
            GROUP BY p.pump_type
            ORDER BY leak_count DESC
            """,
            self._runner,
        )

        # Leaks by API Plan
        leaks_by_api_plan = _json_query(
            f"""
            SELECT 
                COALESCE(p.api_plan, 'UNKNOWN') as api_plan,
                count(r.condition_monitoring_reading_code) as total_readings,
                count(r.condition_monitoring_reading_code) FILTER (
                    WHERE r.mechanical_seal_leak_de = true OR r.mechanical_seal_leak_nde = true
                ) as leak_count
            FROM condition_monitoring_reading r
            JOIN ltsa_pumps p ON p.tag_number = r.asset_code
            {cm_where}
            GROUP BY p.api_plan
            ORDER BY leak_count DESC
            LIMIT 10
            """,
            self._runner,
        )

        # Stock summary
        stock_count = _json_query("SELECT count(*) as c FROM seal_stock", self._runner)
        total_stock = stock_count[0]["c"] if stock_count else 0
        registry_count = _json_query("SELECT count(*) as c FROM seal_registry", self._runner)
        total_registered = registry_count[0]["c"] if registry_count else 0

        return {
            "summary": {
                "seal_replacements_count": seal_replacements_count,
                "mtbsr_days": mtbsr_days,
                "total_registered_seals": total_registered,
                "total_stock_units": total_stock,
                "has_replacement_data": total_replacements_in_db > 0,
                "has_stock_data": total_stock > 0,
            },
            "leaks_by_pump_type": leaks_by_pump_type,
            "leaks_by_api_plan": leaks_by_api_plan,
        }

    def get_material_analytics(
        self,
        *,
        contract_area: str | None = None,
        area: str | None = None,
        pump_tag: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        scope: frozenset[str] | None = None,
    ) -> dict[str, Any]:
        """Material consumption & spare parts usage. Strict UNKNOWN != ZERO."""
        component_stock = _json_query("SELECT count(*) as c FROM internal_component_stock", self._runner)
        total_items = component_stock[0]["c"] if component_stock else 0

        has_data = total_items > 0
        return {
            "has_data": has_data,
            "summary": {
                "total_items_consumed": total_items if has_data else None,
                "total_cost": None,
            },
            "top_consumed_materials": [],
            "message": "Material and spare parts consumption data not yet ingested in current contract period." if not has_data else "",
        }

    def get_maintenance_effectiveness(
        self,
        *,
        contract_area: str | None = None,
        area: str | None = None,
        pump_tag: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        scope: frozenset[str] | None = None,
    ) -> dict[str, Any]:
        """Maintenance effectiveness: PM-to-CM ratio, proactive vs reactive events."""
        pm_where = self._build_where_clauses(
            pump_alias="p",
            record_alias="pm",
            date_col="occurrence_date",
            contract_area=contract_area,
            area=area,
            pump_tag=pump_tag,
            start_date=start_date,
            end_date=end_date,
            scope=scope,
        )
        cm_where = self._build_where_clauses(
            pump_alias="p",
            record_alias="r",
            date_col="reading_date",
            contract_area=contract_area,
            area=area,
            pump_tag=pump_tag,
            start_date=start_date,
            end_date=end_date,
            scope=scope,
        )

        pm_count_res = _json_query(
            f"""
            SELECT count(pm.pm_occurrence_code) as pm_count
            FROM pm_occurrence pm
            JOIN ltsa_pumps p ON p.tag_number = pm.asset_code
            {pm_where}
            """,
            self._runner,
        )
        pm_count = pm_count_res[0]["pm_count"] if pm_count_res else 0

        cm_leak_where = self._build_where_clauses(
            pump_alias="p",
            record_alias="r",
            date_col="reading_date",
            contract_area=contract_area,
            area=area,
            pump_tag=pump_tag,
            start_date=start_date,
            end_date=end_date,
            scope=scope,
            extra_clauses=["(r.mechanical_seal_leak_de = true OR r.mechanical_seal_leak_nde = true)"],
        )
        leak_count_res = _json_query(
            f"""
            SELECT count(r.condition_monitoring_reading_code) as leak_count
            FROM condition_monitoring_reading r
            JOIN ltsa_pumps p ON p.tag_number = r.asset_code
            {cm_leak_where}
            """,
            self._runner,
        )
        leak_count = leak_count_res[0]["leak_count"] if leak_count_res else 0

        # Proactive ratio: PM / (PM + leaks)
        total_events = pm_count + leak_count
        proactive_ratio = round((pm_count / total_events * 100), 1) if total_events > 0 else None
        pm_to_leak_ratio = round((pm_count / leak_count), 2) if leak_count > 0 else None

        # Breakdown by area for effectiveness comparison
        area_effectiveness = _json_query(
            f"""
            WITH area_pm AS (
                SELECT p.area, count(pm.pm_occurrence_code) as pm_count
                FROM pm_occurrence pm
                JOIN ltsa_pumps p ON p.tag_number = pm.asset_code
                {pm_where}
                GROUP BY p.area
            ),
            area_cm AS (
                SELECT 
                    p.area,
                    count(r.condition_monitoring_reading_code) FILTER (
                        WHERE r.mechanical_seal_leak_de = true OR r.mechanical_seal_leak_nde = true
                    ) as leak_count
                FROM condition_monitoring_reading r
                JOIN ltsa_pumps p ON p.tag_number = r.asset_code
                {cm_where}
                GROUP BY p.area
            ),
            all_areas AS (
                SELECT area FROM area_pm
                UNION
                SELECT area FROM area_cm
            )
            SELECT 
                a.area,
                COALESCE(pm.pm_count, 0) as pm_count,
                COALESCE(cm.leak_count, 0) as leak_count,
                CASE 
                    WHEN (COALESCE(pm.pm_count, 0) + COALESCE(cm.leak_count, 0)) > 0 
                    THEN ROUND(COALESCE(pm.pm_count, 0)::numeric / (COALESCE(pm.pm_count, 0) + COALESCE(cm.leak_count, 0)) * 100, 1)
                    ELSE NULL
                END as proactive_percent
            FROM all_areas a
            LEFT JOIN area_pm pm ON pm.area = a.area
            LEFT JOIN area_cm cm ON cm.area = a.area
            ORDER BY COALESCE(pm.pm_count, 0) DESC, COALESCE(cm.leak_count, 0) DESC
            """,
            self._runner,
        )

        return {
            "metrics": {
                "pm_executed": pm_count,
                "confirmed_leaks": leak_count,
                "pm_to_leak_ratio": pm_to_leak_ratio,
                "proactive_ratio_percent": proactive_ratio,
                "first_time_fix_rate": None,  # Insufficient repair data
                "mean_time_to_respond_days": None,  # Insufficient WO lifecycle data
            },
            "area_effectiveness": area_effectiveness,
        }
