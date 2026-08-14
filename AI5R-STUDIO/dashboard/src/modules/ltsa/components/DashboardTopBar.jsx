import { useState } from "react";
import { Badge, SearchBox } from "../../../design-system";
import spacing from "../../../design-system/theme/spacing";
import { DESTINATIONS } from "./QuickNavigationPanel";

/**
 * RC-002 (Executive Dashboard React Implementation): Top Bar.
 *
 * - Global Search: reuses the existing design-system SearchBox unchanged.
 *   Local input state only -- no results list, no search API call. A
 *   plant-wide search backend does not exist yet; wiring one is a
 *   separately-scoped future RC, not fabricated here.
 * - Notifications: static placeholder badge (no notification backend
 *   exists anywhere in LTSA today).
 * - Workspace Selector: reuses QuickNavigationPanel's own `DESTINATIONS`
 *   list (imported, not re-authored) so there is exactly one canonical
 *   destination list for the whole dashboard, consulted by both this
 *   selector and the Quick Navigation panel below it -- not two
 *   independently-maintained navigation lists.
 * - User: static placeholder label (no authentication exists in LTSA).
 */
export default function DashboardTopBar({ onNavigate }) {
  const [searchValue, setSearchValue] = useState("");

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        justifyContent: "space-between",
        gap: spacing.md,
      }}
    >
      <div style={{ flex: "1 1 240px", minWidth: 200 }}>
        <SearchBox
          value={searchValue}
          onChange={setSearchValue}
          placeholder="Search equipment, work orders, drawings…"
        />
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: spacing.md }}>
        <label>
          <span style={{ marginRight: spacing.xs }}>Workspace</span>
          <select
            aria-label="Workspace Selector"
            defaultValue=""
            onChange={(event) => {
              const key = event.target.value;
              if (key) {
                onNavigate(key);
              }
            }}
          >
            <option value="" disabled>
              Jump to workspace…
            </option>
            {DESTINATIONS.map((destination) => (
              <option key={destination.key} value={destination.key} disabled={destination.disabled}>
                {destination.label}
              </option>
            ))}
          </select>
        </label>

        <span aria-label="Notifications" title="No unread notifications">
          <Badge variant="info">Notifications: 0</Badge>
        </span>

        <span aria-label="User">Plant Manager</span>
      </div>
    </div>
  );
}
