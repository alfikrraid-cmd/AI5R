import "./WorkspaceIdentityShell.css";

/**
 * UI-D1.2 -- underline tab strip for the Pump/Mechanical Seal Workspace
 * identity shell, matching Chief's reference (Overview | Performance |
 * Asset360 | Documents | History, etc). A small local component rather
 * than reusing design-system's <Tabs> (which sets its active/inactive
 * colors via inline `style`, not a class -- overriding those from here
 * would need !important on every property; simpler and lower-risk to
 * render this one directly against the existing .ltsa-open-design token
 * scope, same convention InfoRow/StatusSignal/etc. already use).
 */
export default function WorkspaceTabStrip({ items, activeKey, onChange }) {
  return (
    <div className="workspace-tab-strip" role="tablist">
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          role="tab"
          aria-selected={item.key === activeKey}
          className={`workspace-tab${item.key === activeKey ? " is-active" : ""}`}
          onClick={() => onChange(item.key)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
