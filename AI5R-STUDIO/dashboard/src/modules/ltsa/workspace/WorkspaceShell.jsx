import { useEffect, useState } from "react";
import PumpWorkspaceCommandPalette from "../components/PumpWorkspaceCommandPalette";
import { useWorkspaceShortcuts } from "./WorkspaceShortcuts";

export default function WorkspaceShell({
  className = "",
  theme,
  children,
  breadcrumb,
  onToggleTheme,
  commandPaletteActions,
  commandPaletteTag,
}) {
  const [paletteOpen, setPaletteOpen] = useWorkspaceShortcuts();

  useEffect(() => {
    if (!commandPaletteActions) {
      setPaletteOpen(false);
    }
  }, [commandPaletteActions, setPaletteOpen]);

  const showChrome = Boolean(breadcrumb || onToggleTheme || commandPaletteActions);

  return (
    <div className={`pump-workspace-root ${className}`.trim()} data-theme={theme}>
      {showChrome && (
        <header className="chrome-bar">
          <div className="chrome-inner">
            <div className="crumb">{breadcrumb ?? <span>Workspace</span>}</div>

            <div className="chrome-right">
              {commandPaletteActions && (
                <button
                  type="button"
                  className="cmdk-trigger"
                  onClick={() => setPaletteOpen(true)}
                  aria-label="Actions"
                >
                  <span>Actions</span>
                  <kbd>Ctrl K</kbd>
                </button>
              )}

              {onToggleTheme && (
                <button
                  type="button"
                  className="icon-btn"
                  aria-label="Toggle theme"
                  title="Toggle theme"
                  onClick={onToggleTheme}
                >
                  {theme === "dark" ? "☀" : "☾"}
                </button>
              )}
            </div>
          </div>
        </header>
      )}

      {children}

      {commandPaletteActions && (
        <PumpWorkspaceCommandPalette
          open={paletteOpen}
          onClose={() => setPaletteOpen(false)}
          actions={commandPaletteActions}
          pumpTag={commandPaletteTag ?? "Asset"}
        />
      )}
    </div>
  );
}