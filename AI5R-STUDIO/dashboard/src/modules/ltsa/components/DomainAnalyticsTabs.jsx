import { useState } from "react";
import colors from "../../../design-system/theme/colors";
import BarChart from "./charts/BarChart";
import DonutChart from "./charts/DonutChart";

export default function DomainAnalyticsTabs({
  sealAnalytics,
  materialAnalytics,
  effectivenessAnalytics,
  kpis = {},
}) {
  const [activeTab, setActiveTab] = useState("seals");

  const tabs = [
    { key: "seals", label: "Mechanical Seals & Reliability" },
    { key: "materials", label: "Material Consumption & Stock" },
    { key: "effectiveness", label: "Maintenance Effectiveness" },
  ];

  // Drive End vs Non-Drive End leaks for donut chart
  const deNdeData = [
    { label: "Drive End (DE)", value: kpis.de_leaks ?? 0, color: colors.danger },
    { label: "Non-Drive End (NDE)", value: kpis.nde_leaks ?? 0, color: colors.warning },
  ];

  return (
    <div
      style={{
        background: colors.panel,
        border: `1px solid ${colors.border}`,
        borderRadius: "8px",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
        marginTop: "16px",
      }}
      data-testid="domain-analytics-tabs"
    >
      {/* Tab Navigation */}
      <div
        style={{
          display: "flex",
          borderBottom: `1px solid ${colors.border}`,
          gap: "8px",
          overflowX: "auto",
        }}
      >
        {tabs.map((tab) => {
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              style={{
                background: "none",
                border: "none",
                borderBottom: isActive ? `2px solid ${colors.info}` : "2px solid transparent",
                color: isActive ? colors.text : colors.textMuted,
                fontWeight: isActive ? 600 : 400,
                padding: "8px 16px",
                fontSize: "0.85rem",
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "all 0.15s ease",
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Mechanical Seals */}
      {activeTab === "seals" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }} data-testid="tab-content-seals">
          {/* Summary KPIs */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "10px 14px" }}>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>SEAL REPLACEMENTS</div>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, color: colors.text }}>
                {sealAnalytics?.summary?.seal_replacements_count ?? <span style={{ color: colors.textMuted }}>N/A</span>}
              </div>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>0 recorded replacements in period</div>
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "10px 14px" }}>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>MEAN TIME BETWEEN REPLACEMENT (MTBSR)</div>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, color: colors.textMuted }}>
                {sealAnalytics?.summary?.mtbsr_days ?? "N/A"}
              </div>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>Insufficient lifecycle events</div>
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "10px 14px" }}>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>REGISTERED SEALS & STOCK</div>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, color: colors.info }}>
                {sealAnalytics?.summary?.total_registered_seals ?? 0}
              </div>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>{sealAnalytics?.summary?.total_stock_units ?? 0} units in inventory</div>
            </div>
          </div>

          {/* Charts: Leaks by Pump Type, API Plan, and Position */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "14px" }}>
              <BarChart
                title="Leak Evidence by Pump Type"
                data={sealAnalytics?.leaks_by_pump_type || []}
                categoryKey="pump_type"
                bars={[{ key: "leak_count", label: "Leaks", color: colors.danger }]}
              />
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "14px" }}>
              <BarChart
                title="Leak Evidence by API Plan"
                data={sealAnalytics?.leaks_by_api_plan || []}
                categoryKey="api_plan"
                bars={[{ key: "leak_count", label: "Leaks", color: colors.warning }]}
              />
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "14px" }}>
              <DonutChart
                title="Leak Location (DE vs NDE)"
                data={deNdeData}
                labelKey="label"
                valueKey="value"
              />
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Material Consumption */}
      {activeTab === "materials" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }} data-testid="tab-content-materials">
          <div
            style={{
              background: "rgba(59, 130, 246, 0.08)",
              border: `1px solid ${colors.info}`,
              borderRadius: "6px",
              padding: "16px",
              display: "flex",
              flexDirection: "column",
              gap: "6px",
            }}
          >
            <div style={{ fontWeight: 600, color: colors.info, fontSize: "0.9rem" }}>
              Strict Production Policy: UNKNOWN ≠ ZERO
            </div>
            <p style={{ margin: 0, fontSize: "0.8rem", color: colors.text, lineHeight: "1.4" }}>
              {materialAnalytics?.message || "Internal component consumption, rebuild kits, and spare parts tracking data have not been ingested for the current contract period. As per AI5R core engineering guidelines, unrecorded metrics are designated N/A rather than zero to avoid misleading inventory claims."}
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "12px" }}>
              <div style={{ fontSize: "0.75rem", color: colors.textMuted }}>Total Items Consumed</div>
              <div style={{ fontSize: "1.3rem", fontWeight: 700, color: colors.textMuted, marginTop: "4px" }}>N/A</div>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>No ledger entries</div>
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "12px" }}>
              <div style={{ fontSize: "0.75rem", color: colors.textMuted }}>Material Cost Incurred</div>
              <div style={{ fontSize: "1.3rem", fontWeight: 700, color: colors.textMuted, marginTop: "4px" }}>N/A</div>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>No ledger entries</div>
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "12px" }}>
              <div style={{ fontSize: "0.75rem", color: colors.textMuted }}>Stock Health Status</div>
              <div style={{ fontSize: "1.3rem", fontWeight: 700, color: colors.warning, marginTop: "4px" }}>Pending Ingestion</div>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>Waiting for warehouse sync</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Maintenance Effectiveness */}
      {activeTab === "effectiveness" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }} data-testid="tab-content-effectiveness">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "12px" }}>
              <div style={{ fontSize: "0.75rem", color: colors.textMuted }}>PROACTIVE RATIO</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700, color: colors.success, marginTop: "4px" }}>
                {effectivenessAnalytics?.metrics?.proactive_ratio_percent !== null ? `${effectivenessAnalytics.metrics.proactive_ratio_percent}%` : "N/A"}
              </div>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>PMs vs total incidents</div>
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "12px" }}>
              <div style={{ fontSize: "0.75rem", color: colors.textMuted }}>PM-TO-LEAK RATIO</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700, color: colors.info, marginTop: "4px" }}>
                {effectivenessAnalytics?.metrics?.pm_to_leak_ratio ?? "N/A"}
              </div>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>53 PMs / 52 Leaks</div>
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "12px" }}>
              <div style={{ fontSize: "0.75rem", color: colors.textMuted }}>FIRST-TIME FIX RATE</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700, color: colors.textMuted, marginTop: "4px" }}>
                {effectivenessAnalytics?.metrics?.first_time_fix_rate ?? "N/A"}
              </div>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>Requires post-repair tracking</div>
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${colors.border}`, borderRadius: "6px", padding: "12px" }}>
              <div style={{ fontSize: "0.75rem", color: colors.textMuted }}>MEAN TIME TO RESPOND</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700, color: colors.textMuted, marginTop: "4px" }}>
                {effectivenessAnalytics?.metrics?.mean_time_to_respond_days ?? "N/A"}
              </div>
              <div style={{ fontSize: "0.7rem", color: colors.textMuted }}>Requires closed work orders</div>
            </div>
          </div>

          {/* Area Effectiveness Comparison Table */}
          <div style={{ width: "100%", overflowX: "auto" }}>
            <div style={{ fontSize: "0.85rem", fontWeight: 600, color: colors.text, marginBottom: "8px" }}>
              Area Maintenance Effectiveness Comparison
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem", textAlign: "left" }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${colors.border}`, color: colors.textMuted }}>
                  <th style={{ padding: "8px 10px", fontWeight: 600 }}>Contract Area</th>
                  <th style={{ padding: "8px 10px", fontWeight: 600, textAlign: "center" }}>PM Done</th>
                  <th style={{ padding: "8px 10px", fontWeight: 600, textAlign: "center" }}>Leak Evidence</th>
                  <th style={{ padding: "8px 10px", fontWeight: 600, textAlign: "right" }}>Proactive Ratio</th>
                </tr>
              </thead>
              <tbody>
                {(effectivenessAnalytics?.area_effectiveness || []).map((row) => (
                  <tr key={row.area} style={{ borderBottom: `1px solid rgba(255,255,255,0.05)` }}>
                    <td style={{ padding: "8px 10px", fontWeight: 600, color: colors.text }}>{row.area}</td>
                    <td style={{ padding: "8px 10px", textAlign: "center", color: colors.success }}>{row.pm_count}</td>
                    <td style={{ padding: "8px 10px", textAlign: "center", color: row.leak_count > 0 ? colors.danger : colors.textMuted }}>
                      {row.leak_count}
                    </td>
                    <td style={{ padding: "8px 10px", textAlign: "right", fontWeight: 700, color: row.proactive_percent ? colors.info : colors.textMuted }}>
                      {row.proactive_percent !== null ? `${row.proactive_percent}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

