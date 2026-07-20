import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

export default function AssetSelector({ assets, selectedTag, onSelect }) {
  return (
    <div style={{ marginBottom: spacing.md }}>
      <label htmlFor="asset-selector" style={{ display: "block", color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>
        Select Asset
      </label>

      <select
        id="asset-selector"
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
