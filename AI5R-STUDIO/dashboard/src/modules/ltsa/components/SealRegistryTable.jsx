import { useMemo } from "react";
import { Table } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import { formatDrawingSummary, formatCompatiblePumps, formatAvailableStock } from "../utils/sealMapping";

function buildColumns(onSelect) {
  return [
    {
      key: "seal",
      header: "Mechanical Seal",
      render: (_, item) => (
        <div>
          <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
            {item.seal_type ? <span>{item.seal_type}</span> : null}
            {item.code && item.code !== item.seal_type ? (
              <span style={{ color: colors.textMuted, fontWeight: 400, fontSize: "12px" }}>
                (<span>{item.code}</span>)
              </span>
            ) : null}
          </div>
          {item.name && item.name !== item.code && item.name !== item.seal_type ? (
            <div style={{ fontSize: "12px", color: colors.textMuted, marginTop: "2px" }}>
              {item.name}
            </div>
          ) : null}
        </div>
      ),
    },
    {
      key: "size",
      header: "Size",
      render: (_, item) => (
        <span>{item.nominal_size || item.physical_stock_size || item.shaftSize || item.size || "—"}</span>
      ),
    },
    {
      key: "drawing",
      header: "GPN / Drawing",
      render: (_, item) => {
        const gpn = item.complete_seal_gpn || item.gpnJohnCrane;
        const drawing = item.drawing_reference;
        return (
          <div>
            {gpn ? <div style={{ fontSize: "12px", fontWeight: 500 }}>{gpn}</div> : null}
            {drawing ? (
              <div
                title={drawing}
                style={{ fontSize: "12px", color: colors.textMuted, cursor: "help" }}
              >
                {formatDrawingSummary(drawing)}
              </div>
            ) : !gpn ? (
              <span style={{ color: colors.textMuted }}>—</span>
            ) : null}
          </div>
        );
      },
    },
    {
      key: "compatiblePumps",
      header: "Compatible Pumps",
      render: (_, item) => (
        <span style={{ fontWeight: 500 }}>
          {item.compatiblePumpsLabel || formatCompatiblePumps(item.compatiblePumps)}
        </span>
      ),
    },
    {
      key: "availableStock",
      header: "Available Stock",
      render: (_, item) => {
        const label =
          item.availableLabel ??
          formatAvailableStock(
            item.quantity_available ?? item.quantity_on_hand,
            item.hasStockRecord !== false
          );
        const isLow =
          item.hasStockRecord !== false &&
          (item.quantity_available ?? item.quantity_on_hand) === 0;
        const isUnmanaged = item.hasStockRecord === false || label === "N/A";
        return (
          <span
            style={{
              fontWeight: 600,
              color: isLow ? colors.error : isUnmanaged ? colors.textMuted : colors.text,
            }}
          >
            {label}
          </span>
        );
      },
    },
    {
      key: "status",
      header: "Status",
      render: (_, item) => {
        const status = item.verification_status || item.status || "UNKNOWN";
        let bg = "rgba(100, 116, 139, 0.2)";
        let textCol = colors.textMuted;
        if (status === "CONFIRMED" || status === "ACTIVE") {
          bg = "rgba(34, 197, 94, 0.15)";
          textCol = "#4ade80";
        } else if (status === "VERIFY" || status === "STANDBY" || status === "ALERT") {
          bg = "rgba(234, 179, 8, 0.15)";
          textCol = "#facc15";
        } else if (
          status === "VERIFY_CONFIGURATION" ||
          status === "VERIFY_SIZE_COMPATIBILITY" ||
          status === "FAULT"
        ) {
          bg = "rgba(239, 68, 68, 0.15)";
          textCol = "#f87171";
        }
        return (
          <span
            style={{
              display: "inline-block",
              padding: "2px 8px",
              borderRadius: "4px",
              fontSize: "11px",
              fontWeight: 600,
              background: bg,
              color: textCol,
            }}
          >
            {status}
          </span>
        );
      },
    },
    {
      key: "action",
      header: "Action",
      render: (_, item) => (
        <button
          type="button"
          style={{
            background: "transparent",
            border: `1px solid ${colors.border}`,
            borderRadius: "4px",
            color: colors.primary ?? "#38bdf8",
            padding: "2px 8px",
            fontSize: "12px",
            cursor: "pointer",
          }}
          onClick={(e) => {
            e.stopPropagation();
            onSelect?.(item.id || item.code);
          }}
        >
          Details
        </button>
      ),
    },
  ];
}

export default function SealRegistryTable({ seals, selectedCode, onSelect }) {
  const columns = useMemo(() => buildColumns(onSelect), [onSelect]);
  const normalizedSeals = (seals ?? []).map((s) => ({
    ...s,
    id: s.id || s.code,
  }));
  const selectedItem = normalizedSeals.find(
    (s) => s.id === selectedCode || s.code === selectedCode
  );
  const selectedKey = selectedItem ? selectedItem.id : selectedCode;

  return (
    <Table
      columns={columns}
      data={normalizedSeals}
      rowKey="id"
      selectedKey={selectedKey}
      onRowClick={(seal) => onSelect?.(seal.id || seal.code)}
    />
  );
}

