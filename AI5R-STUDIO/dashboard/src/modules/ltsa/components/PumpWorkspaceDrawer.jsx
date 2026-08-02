import { IconClose } from "./PumpWorkspaceIcons";

/** Ported 1:1 from pump-workspace.html's shared slide-in Drawer. */
export default function PumpWorkspaceDrawer({ open, onClose, title, children }) {
  return (
    <>
      <div className="drawer-overlay" data-open={open} onClick={onClose} />
      <div className="drawer" data-open={open} role="dialog" aria-label={title}>
        <div className="drawer-head">
          <h3 className="drawer-title">{title}</h3>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close" data-od-id="drawer-close">
            <IconClose width="16" height="16" />
          </button>
        </div>
        <div className="drawer-body">{children}</div>
      </div>
    </>
  );
}
