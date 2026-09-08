import { useEffect, useRef, useState } from "react";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

// AI5R-CMON-UX-001 -- adds a search filter in front of the existing
// native <select>, rather than replacing it with a bespoke ARIA
// combobox widget. Deliberate: this component is shared by LTSAWorkspace,
// MaintenanceHistory, ConditionMonitoringWorkspace, CreatePMScheduleModal,
// and every CMon entry surface -- a native <select> is trivially
// keyboard/mouse/touch accessible everywhere those already work, and
// every existing test/consumer asserting role "combobox" (the implicit
// ARIA role of a single-select <select>) and role "option" keeps working
// completely unchanged. The search box only narrows which <option>s are
// currently rendered; it never changes what gets selected or what value
// is reported to onSelect -- that is always the real asset's own `tag`,
// exactly as before.
//
// Matching is normalization-for-MATCHING-ONLY: punctuation/spacing is
// stripped from both the query and each candidate before comparing, so
// "110p8a", "110-p-8a", and "110 P 8A" all find "110-P-8A" -- but the
// canonical tag itself, and the value ever passed to onSelect, is never
// rewritten or reconstructed client-side (Section C: never invent pump
// tags). Matches on the asset's `name` too, when present, so searching
// by description works the same way.
function normalizeForSearch(value) {
  return (value ?? "").toString().toLowerCase().replace(/[^a-z0-9]/g, "");
}

// `label`/`id` are optional and default to this component's original
// values, so every pre-existing caller keeps working unchanged.
// `autoFocus` is a new, opt-in-only prop (default false) -- callers that
// swap a "Selected Equipment" card back to this selector (e.g. via a
// "Change" action) can request the search box receive focus immediately;
// every existing caller that never passes it keeps behaving exactly as
// before.
export default function AssetSelector({
  assets,
  selectedTag,
  onSelect,
  label = "Select Asset",
  id = "asset-selector",
  autoFocus = false,
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const searchInputRef = useRef(null);
  const normalizedTerm = normalizeForSearch(searchTerm);

  useEffect(() => {
    if (autoFocus) {
      searchInputRef.current?.focus();
    }
    // Intentionally mount-only: this reflects a caller's one-time
    // "just returned to the selector" request, not a live prop to keep
    // re-applying on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const filteredAssets = normalizedTerm
    ? assets.filter(
        (asset) =>
          normalizeForSearch(asset.tag).includes(normalizedTerm) || normalizeForSearch(asset.name).includes(normalizedTerm)
      )
    : assets;
  const searchId = `${id}-search`;

  return (
    <div style={{ marginBottom: spacing.md }}>
      <label htmlFor={id} style={{ display: "block", color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>
        {label}
      </label>

      <label htmlFor={searchId} style={{ display: "block", color: colors.textMuted, fontSize: 11, marginBottom: 2 }}>
        Search tag or name
      </label>
      <input
        ref={searchInputRef}
        id={searchId}
        type="text"
        value={searchTerm}
        onChange={(event) => setSearchTerm(event.target.value)}
        placeholder="e.g. 110p8a"
        autoComplete="off"
        style={{
          width: "100%",
          maxWidth: 320,
          boxSizing: "border-box",
          background: colors.panel,
          color: colors.text,
          border: `1px solid ${colors.border}`,
          borderRadius: spacing.xs,
          padding: `${spacing.xs}px ${spacing.sm}px`,
          marginBottom: spacing.xs,
        }}
      />

      <select
        id={id}
        value={selectedTag ?? ""}
        onChange={(event) => onSelect(event.target.value || null)}
        style={{
          width: "100%",
          maxWidth: 320,
          boxSizing: "border-box",
          background: colors.panel,
          color: colors.text,
          border: `1px solid ${colors.border}`,
          borderRadius: spacing.xs,
          padding: `${spacing.xs}px ${spacing.sm}px`,
        }}
      >
        <option value="">Select a pump...</option>

        {filteredAssets.map((asset) => (
          <option key={asset.tag} value={asset.tag}>
            {asset.tag} — {asset.name}
          </option>
        ))}
      </select>

      {normalizedTerm && filteredAssets.length === 0 && (
        <p style={{ color: colors.textMuted, fontSize: 12, margin: `${spacing.xs}px 0 0` }} role="status">
          No pumps match "{searchTerm}".
        </p>
      )}
    </div>
  );
}
