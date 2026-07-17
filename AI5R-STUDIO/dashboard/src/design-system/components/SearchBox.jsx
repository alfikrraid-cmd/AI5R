export default function SearchBox({ value, onChange, placeholder = "Search..." }) {
  return (
    <input
      type="search"
      role="searchbox"
      className="ds-search-box"
      value={value}
      placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
