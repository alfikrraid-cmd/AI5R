import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

// AI5R-PHASE4E2 -- `label`/`id` are optional and default to this
// component's original values, so every pre-existing caller (LTSAWorkspace,
// MaintenanceHistory, ConditionMonitoringWorkspace -- all asserting
// getByLabelText("Select Asset") in their own tests) keeps working
// unchanged. CreatePMScheduleModal is the first caller to override them
// (label="Pump"), reusing this same canonical pump-master selector instead
// of a free-text field (Section C: never invent pump tags).
export default function AssetSelector({ assets, selectedTag, onSelect, label = "Select Asset", id = "asset-selector" }) {
  return (
    <div style={{ marginBottom: spacing.md }}>
      <label htmlFor={id} style={{ display: "block", color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>
        {label}
      </label>

      <select
        id={id}
        value={selectedTag ?? ""}
        onChange={(event) => onSelect(event.target.value || null)}
        style={{
          background: colors.panel,
          color: colors.text,
          border: `1px solid ${colors.border}`,
          borderRadius: spacing.xs,
          padding: `${spacing.xs}px ${spacing.sm}px`,
          minWidth: 320,
        }}
      >
        <option value="">Select a pump...</option>

        {assets.map((asset) => (
          <option key={asset.tag} value={asset.tag}>
            {asset.tag} — {asset.name}
          </option>
        ))}
      </select>
    </div>
  );
}
