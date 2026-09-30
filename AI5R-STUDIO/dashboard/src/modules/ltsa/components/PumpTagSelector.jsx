import { useEffect, useMemo, useRef, useState } from "react";

function searchValue(value) {
  return String(value ?? "").toLowerCase();
}

function pumpTag(pump) {
  return pump?.tag_number ?? pump?.tag ?? pump?.asset_code ?? pump?.assetTag ?? "";
}

function pumpArea(pump) {
  return pump?.area ?? pump?.area_name ?? pump?.unit ?? "";
}

export default function PumpTagSelector({ pumps = [], currentTag, loading, error, onSelect }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlighted, setHighlighted] = useState(0);
  const rootRef = useRef(null);
  const inputRef = useRef(null);

  const options = useMemo(() => pumps
    .map((pump) => ({ pump, tag: pumpTag(pump), area: pumpArea(pump) }))
    .filter((option) => option.tag), [pumps]);
  const filtered = useMemo(() => {
    const needle = searchValue(query);
    return (needle ? options.filter(({ tag, area }) => searchValue(tag).includes(needle) || searchValue(area).includes(needle)) : options).slice(0, 20);
  }, [options, query]);

  useEffect(() => {
    setQuery("");
    setHighlighted(0);
    setOpen(false);
  }, [currentTag]);

  useEffect(() => {
    const close = (event) => {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const choose = (option) => {
    if (!option) return;
    setOpen(false);
    setQuery("");
    onSelect(option.tag);
  };

  const handleKeyDown = (event) => {
    if (event.key === "Escape") {
      setOpen(false);
      setQuery("");
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setHighlighted((value) => Math.min(value + 1, Math.max(filtered.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlighted((value) => Math.max(value - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(filtered[highlighted]);
    }
  };

  return (
    <div ref={rootRef} className="asset360-pump-selector" data-testid="pump-tag-selector">
      <button type="button" className="asset360-pump-selector-trigger" aria-haspopup="listbox" aria-expanded={open} onClick={() => { setOpen(true); inputRef.current?.focus(); }}>
        <b>{currentTag || "Select pump"}</b><span aria-hidden="true"> ▾</span>
      </button>
      {open && (
        <div className="asset360-pump-selector-menu" role="dialog" aria-label="Select pump">
          <input ref={inputRef} value={query} onChange={(event) => { setQuery(event.target.value); setHighlighted(0); }} onKeyDown={handleKeyDown} placeholder="Search pump tag or area" aria-label="Search pump tag" autoComplete="off" />
          {loading ? <div role="status">Loading pumps…</div> : error ? <div role="alert">Unable to load pumps.</div> : filtered.length ? (
            <ul role="listbox" aria-label="Pump tags">
              {filtered.map((option, index) => <li key={option.tag} role="option" aria-selected={option.tag === currentTag} className={option.tag === currentTag ? "is-current" : index === highlighted ? "is-highlighted" : ""} onMouseDown={(event) => { event.preventDefault(); choose(option); }}>
                <span>{option.tag}</span>{option.area ? <small>{option.area}</small> : null}
              </li>)}
            </ul>
          ) : <div role="status">No pumps match “{query}”.</div>}
        </div>
      )}
    </div>
  );
}
