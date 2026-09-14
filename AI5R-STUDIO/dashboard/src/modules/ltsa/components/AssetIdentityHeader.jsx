import "./WorkspaceIdentityShell.css";

/**
 * UI-D1.2 -- shared identity header for the Pump/Mechanical Seal
 * Workspace, matching Chief's reference: an icon representation, the
 * asset's tag/code as the big title, a name/subtitle line, and 1-2
 * compact "health card" slots on the right (real values only -- each
 * caller decides what real field, if any, backs each card; N/A is
 * rendered honestly when nothing real exists, never fabricated).
 */
export function HealthCard({ label, value, tone = "neutral" }) {
  return (
    <div className={`workspace-health-card tone-${tone}`}>
      <span className="workspace-health-card-label">{label}</span>
      <strong className="workspace-health-card-value">{value ?? "N/A"}</strong>
    </div>
  );
}

export default function AssetIdentityHeader({ icon, tag, name, subtitle, onBack, backLabel = "Back to Dashboard", children }) {
  return (
    <div className="workspace-identity-shell">
      {onBack ? (
        <button type="button" className="workspace-back-link" onClick={onBack}>
          ‹ {backLabel}
        </button>
      ) : null}
      <div className="workspace-identity-row">
        <div className="workspace-identity-main">
          {icon ? <div className="workspace-identity-icon">{icon}</div> : null}
          <div>
            <h1 className="workspace-identity-tag">{tag}</h1>
            <p className="workspace-identity-subtitle">
              {name}
              {subtitle ? <span className="workspace-identity-subtitle-sep"> · {subtitle}</span> : null}
            </p>
          </div>
        </div>
        {children ? <div className="workspace-health-cards">{children}</div> : null}
      </div>
    </div>
  );
}
