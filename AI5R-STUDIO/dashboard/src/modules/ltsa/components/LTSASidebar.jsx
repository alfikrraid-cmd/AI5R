import "./LTSASidebar.css";
import { NAV_ICONS, IconMore } from "./LTSANavIcons";

// Persistent left navigation for the LTSA engineering workspace
// (UI-D1.2 -- light operational sidebar per Chief's reference, replacing
// UI-D1's dark navy panel). Renders each item with the same
// role="tab"/aria-selected contract the design-system Tabs bar it
// replaces already used, so it is a purely visual swap: every existing
// LTSAWorkspace.test.jsx / LTSAWorkspace.consolidation.test.jsx
// assertion (getByRole("tab", { name })) keeps passing unchanged -- the
// icon is decorative (aria-hidden), never part of the accessible name.
export default function LTSASidebar({ groups = [], activeKey, onChange }) {
  return (
    <nav className="ltsa-sidebar" aria-label="LTSA workspace navigation">
      <div className="ltsa-sidebar-brand">
        <span className="ltsa-sidebar-brand-mark" aria-hidden="true">A5</span>
        <span className="ltsa-sidebar-brand-name">
          <strong>AI5R</strong>
          <span>LTSA</span>
        </span>
      </div>

      <div className="ltsa-sidebar-scroll" role="tablist">
        {groups.map((group) => (
          <div className="ltsa-sidebar-group" key={group.heading ?? "primary"}>
            {group.heading ? <div className="ltsa-sidebar-heading">{group.heading}</div> : null}

            {group.items.map((item) => {
              const isActive = item.key === activeKey;
              const ItemIcon = NAV_ICONS[item.key] ?? IconMore;

              return (
                <button
                  key={item.key}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`ltsa-sidebar-item${isActive ? " is-active" : ""}`}
                  onClick={() => onChange(item.key)}
                >
                  <span className="ltsa-sidebar-item-icon" aria-hidden="true">
                    <ItemIcon />
                  </span>
                  {item.label}
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </nav>
  );
}
