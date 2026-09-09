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
}) {
  const [compatibilityRecords, setCompatibilityRecords] = useState(propCompatibilityRecords ?? []);
  const [pumps, setPumps] = useState(propPumps ?? []);
  const [loading, setLoading] = useState(false);
  const [expandedSeals, setExpandedSeals] = useState(new Set());

  useEffect(() => {
    if (propCompatibilityRecords) setCompatibilityRecords(propCompatibilityRecords);
  }, [propCompatibilityRecords]);

  useEffect(() => {
    if (propPumps) setPumps(propPumps);
  }, [propPumps]);

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

    Promise.all([fetchCompat, fetchPumps])
      .then(([compat, pumpList]) => {
        if (active) {
          if (!propCompatibilityRecords) {
            setCompatibilityRecords(Array.isArray(compat) ? compat : []);
          }
          if (!propPumps) {
            setPumps(Array.isArray(pumpList) ? pumpList : []);
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
  }, [items, propCompatibilityRecords, propPumps]);

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

    const matchingPumps = compatibilityRecords
      .filter((record) => record.seal_code === sealCode)
      .filter((record) => authorizedPumpsByTag.has(record.pump_tag_number))
      .map((record) => {
        const pump = authorizedPumpsByTag.get(record.pump_tag_number);
        const area = pump?.area || "—";
        return {
          tag: record.pump_tag_number,
          area,
          ma: resolveAreaMA(area),
          status: pump?.status || "UNKNOWN",
        };
      });

    const count = matchingPumps.length;

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
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: spacing.xs,
          }}
        >
          <span style={{ fontSize: 12, color: colors.textMuted }} data-testid={`compat-count-${item.id}`}>
            {loading ? "Loading compatible pumps…" : `Compatible with ${count} pump${count === 1 ? "" : "s"}`}
          </span>
          {count > 0 && (
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

        {isExpanded && count > 0 && (
          <div
            data-testid={`compat-pumps-table-${item.id}`}
            style={{
              marginTop: spacing.xs,
              maxHeight: 200,
              overflowY: "auto",
              border: `1px solid ${colors.border}`,
              borderRadius: spacing.xs,
              background: colors.background,
            }}
          >
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
                {matchingPumps.map((pump) => (
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
