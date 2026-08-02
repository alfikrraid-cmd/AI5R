import { useEffect, useMemo, useRef, useState } from "react";

/**
 * Ported 1:1 from DESIGN/LTSA/PUMP_WORKSPACE/pump-workspace.html's
 * CommandPalette. `actions` is [{ id, label, hint, icon, run }]; wiring
 * to real handlers happens in the page, not here.
 */
export default function PumpWorkspaceCommandPalette({ open, onClose, actions, pumpTag }) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return actions;
    return actions.filter(
      (action) => action.label.toLowerCase().includes(q) || action.hint.toLowerCase().includes(q)
    );
  }, [query, actions]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
      setTimeout(() => inputRef.current && inputRef.current.focus(), 20);
    }
  }, [open]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  function onKeyDown(event) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((a) => Math.min(a + 1, filtered.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const action = filtered[active];
      if (action) {
        action.run();
        onClose();
      }
    } else if (event.key === "Escape") {
      onClose();
    }
  }

  return (
    <div className="cmdk-overlay" data-open={open} onClick={onClose}>
      <div className="cmdk-panel" onClick={(event) => event.stopPropagation()}>
        <div className="cmdk-input-row">
          <input
            ref={inputRef}
            className="cmdk-input"
            placeholder={`Cari aksi untuk ${pumpTag}...`}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onKeyDown}
            data-od-id="cmdk-input"
          />
        </div>
        <div className="cmdk-list">
          {filtered.length === 0 && <div className="cmdk-empty">Tidak ada aksi yang cocok</div>}
          {filtered.map((action, index) => (
            <div
              key={action.id}
              className="cmdk-item"
              data-active={index === active}
              onMouseEnter={() => setActive(index)}
              onClick={() => {
                action.run();
                onClose();
              }}
              data-od-id={`cmdk-item-${action.id}`}
            >
              <action.icon width="16" height="16" />
              <span>{action.label}</span>
              <span className="cmdk-item-hint">{action.hint}</span>
            </div>
          ))}
        </div>
        <div className="cmdk-footer">
          <div className="hints">
            <span>↑↓ pilih</span>
            <span>↵ jalankan</span>
          </div>
          <span>esc tutup</span>
        </div>
      </div>
    </div>
  );
}
