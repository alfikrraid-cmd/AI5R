import { useEffect, useState } from "react";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import * as ai5rClient from "../../../api/ai5rClient";
import { resolveAreaMA } from "../utils/areaMapping";

function EmptySection({ title }) {
  return (
    <div className="eng-empty">
      <h4>{title}</h4>
    </div>
  );
}

export default function KnowledgeCompatibleSeals({
  items = [],
  emptyTitle = "Belum ada seal kompatibel",
  compatibilityRecords: propCompatibilityRecords,
  pumps: propPumps,
  seals: propSeals,
}) {
  const [compatibilityRecords, setCompatibilityRecords] = useState(propCompatibilityRecords ?? []);
  const [pumps, setPumps] = useState(propPumps ?? []);
  const [seals, setSeals] = useState(propSeals ?? []);
  const [loading, setLoading] = useState(false);
  const [expandedSeals, setExpandedSeals] = useState(new Set());
  const [activeTabBySeal, setActiveTabBySeal] = useState({});

  useEffect(() => {
    if (propCompatibilityRecords) setCompatibilityRecords(propCompatibilityRecords);
  }, [propCompatibilityRecords]);

  useEffect(() => {
    if (propPumps) setPumps(propPumps);
  }, [propPumps]);

  useEffect(() => {
    if (propSeals) setSeals(propSeals);
  }, [propSeals]);

  useEffect(() => {
    if (propCompatibilityRecords && propPumps) {
      return undefined;
    }
    let active = true;
    if (!items || items.length === 0) {
      return undefined;
    }

    if (!("getSealCompatibility" in ai5rClient) || !("getPumps" in ai5rClient)) {
      return undefined;
    }

    setLoading(true);
    const fetchCompat = typeof ai5rClient.getSealCompatibility === "function" ? ai5rClient.getSealCompatibility().catch(() => []) : Promise.resolve([]);
    const fetchPumps = typeof ai5rClient.getPumps === "function" ? ai5rClient.getPumps().catch(() => []) : Promise.resolve([]);
    const fetchSeals = typeof ai5rClient.getSeals === "function" ? ai5rClient.getSeals().catch(() => []) : Promise.resolve([]);

    Promise.all([fetchCompat, fetchPumps, fetchSeals])
      .then(([compat, pumpList, sealList]) => {
        if (active) {
          if (!propCompatibilityRecords) {
            setCompatibilityRecords(Array.isArray(compat) ? compat : []);
          }
          if (!propPumps) {
            setPumps(Array.isArray(pumpList) ? pumpList : []);
          }
          if (!propSeals) {
            setSeals(Array.isArray(sealList) ? sealList : []);
          }
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [items, propCompatibilityRecords, propPumps, propSeals]);

  if (!items || items.length === 0) {
    return <EmptySection title={emptyTitle} />;
  }

  const authorizedPumpsByTag = new Map(
    pumps.map((pump) => [pump.tag_number || pump.tag, pump])
  );

  function toggleExpand(sealId) {
    setExpandedSeals((current) => {
      const next = new Set(current);
      if (next.has(sealId)) {
        next.delete(sealId);
      } else {
        next.add(sealId);
      }
      return next;
    });
  }

  return items.map((item) => {
    const sealCode = item.id || item.meta;
    const isExpanded = expandedSeals.has(item.id);
    const currentTab = activeTabBySeal[item.id] || "variant";

    // 1. Variant-specific matching pumps (deduplicated by pump tag, strictly authorized)
    const matchingPumpsMap = new Map();
    for (const record of compatibilityRecords) {
      if (record.seal_code === sealCode && authorizedPumpsByTag.has(record.pump_tag_number)) {
        if (!matchingPumpsMap.has(record.pump_tag_number)) {
          const pump = authorizedPumpsByTag.get(record.pump_tag_number);
          const area = pump?.area || "—";
          matchingPumpsMap.set(record.pump_tag_number, {
            tag: record.pump_tag_number,
            area,
            ma: resolveAreaMA(area),
            status: pump?.status || "UNKNOWN",
          });
        }
      }
    }
    const matchingPumps = Array.from(matchingPumpsMap.values());
    const count = matchingPumps.length;

    // 2. Family-level matching pumps (deduplicated by pump tag, strictly authorized)
    const familyName = item.name;
    const familySealCodes = new Set();
    if (familyName) {
      for (const s of seals) {
        if (s.seal_name === familyName || s.name === familyName) {
          if (s.seal_code) familySealCodes.add(s.seal_code);
        }
      }
    }

    const familyPumpsMap = new Map();
    for (const record of compatibilityRecords) {
      const isFamily =
        familySealCodes.size > 0
          ? familySealCodes.has(record.seal_code)
          : (record.seal_code === sealCode || (familyName && record.seal_code?.includes(familyName)));

      if (isFamily && authorizedPumpsByTag.has(record.pump_tag_number)) {
        if (!familyPumpsMap.has(record.pump_tag_number)) {
          const pump = authorizedPumpsByTag.get(record.pump_tag_number);
          const area = pump?.area || "—";
          familyPumpsMap.set(record.pump_tag_number, {
            tag: record.pump_tag_number,
            area,
            ma: resolveAreaMA(area),
            status: pump?.status || "UNKNOWN",
          });
        }
      }
    }
    const familyPumps = Array.from(familyPumpsMap.values());
    const familyCount = familyPumps.length;
    const showFamilyInfo = Boolean(familyName && familyName !== sealCode && familyCount > 0);

    const displayPumps = currentTab === "family" && showFamilyInfo ? familyPumps : matchingPumps;
    const hasAnyPumps = count > 0 || (showFamilyInfo && familyCount > 0);

    return (
      <div className="part-item" key={item.id} data-testid={`compat-seal-item-${item.id}`}>
        <div className="part-row">
          <span className="part-name">{item.name}</span>
          {item.flag ? <span className={`stock-flag ${item.flag}`}>{item.flagLabel ?? item.flag}</span> : null}
        </div>
        <div className="part-meta">{item.meta}</div>

        <div
          style={{
            marginTop: spacing.xs,
            display: "flex",
            flexDirection: "column",
            gap: 2,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: spacing.xs,
            }}
          >
            <span style={{ fontSize: 12, color: colors.textMuted }} data-testid={`compat-count-${item.id}`}>
              {loading
                ? "Loading compatible pumps…"
                : `Compatible with ${count} pump${count === 1 ? "" : "s"} (variant ${sealCode})`}
            </span>
            {hasAnyPumps && (
              <button
                type="button"
                onClick={() => toggleExpand(item.id)}
                aria-expanded={isExpanded}
                data-testid={`compat-toggle-${item.id}`}
                style={{
                  background: "transparent",
                  border: "none",
                  color: colors.info,
                  cursor: "pointer",
                  fontSize: 12,
                  padding: "2px 4px",
                  textDecoration: "underline",
                }}
              >
                {isExpanded ? "Hide pumps ▴" : "View all ▾"}
              </button>
            )}
          </div>
          {showFamilyInfo && !loading && (
            <span
              style={{ fontSize: 11, color: colors.textMuted }}
              data-testid={`compat-family-count-${item.id}`}
            >
              {familyName} family: {familyCount} distinct pump{familyCount === 1 ? "" : "s"} in scope
            </span>
          )}
        </div>

        {isExpanded && hasAnyPumps && (
          <div
            data-testid={`compat-pumps-table-${item.id}`}
            style={{
              marginTop: spacing.xs,
              maxHeight: 220,
              overflowY: "auto",
              border: `1px solid ${colors.border}`,
              borderRadius: spacing.xs,
              background: colors.background,
              padding: spacing.xs,
            }}
          >
            {showFamilyInfo && familyCount > count && (
              <div
                style={{
                  display: "flex",
                  gap: spacing.xs,
                  marginBottom: spacing.xs,
                }}
              >
                <button
                  type="button"
                  onClick={() =>
                    setActiveTabBySeal((prev) => ({ ...prev, [item.id]: "variant" }))
                  }
                  data-testid={`compat-tab-variant-${item.id}`}
                  style={{
                    padding: "2px 8px",
                    fontSize: 11,
                    borderRadius: spacing.xs,
                    border: `1px solid ${currentTab === "variant" ? colors.info : colors.border}`,
                    background: currentTab === "variant" ? colors.panel : "transparent",
                    color: currentTab === "variant" ? colors.info : colors.textMuted,
                    cursor: "pointer",
                    fontWeight: currentTab === "variant" ? 600 : 400,
                  }}
                >
                  Variant ({count})
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setActiveTabBySeal((prev) => ({ ...prev, [item.id]: "family" }))
                  }
                  data-testid={`compat-tab-family-${item.id}`}
                  style={{
                    padding: "2px 8px",
                    fontSize: 11,
                    borderRadius: spacing.xs,
                    border: `1px solid ${currentTab === "family" ? colors.info : colors.border}`,
                    background: currentTab === "family" ? colors.panel : "transparent",
                    color: currentTab === "family" ? colors.info : colors.textMuted,
                    cursor: "pointer",
                    fontWeight: currentTab === "family" ? 600 : 400,
                  }}
                >
                  All {familyName} Family ({familyCount})
                </button>
              </div>
            )}
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${colors.border}`, color: colors.textMuted, background: colors.panel }}>
                  <th style={{ padding: "4px 8px", textAlign: "left" }}>Tag</th>
                  <th style={{ padding: "4px 8px", textAlign: "left" }}>Area</th>
                  <th style={{ padding: "4px 8px", textAlign: "left" }}>MA</th>
                  <th style={{ padding: "4px 8px", textAlign: "left" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {displayPumps.map((pump) => (
                  <tr key={pump.tag} style={{ borderBottom: `1px solid ${colors.border}` }}>
                    <td style={{ padding: "4px 8px", color: colors.text, fontWeight: 600 }}>{pump.tag}</td>
                    <td style={{ padding: "4px 8px", color: colors.textMuted }}>{pump.area}</td>
                    <td style={{ padding: "4px 8px", color: colors.textMuted }}>{pump.ma}</td>
                    <td style={{ padding: "4px 8px", color: colors.text }}>{pump.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  });
}
