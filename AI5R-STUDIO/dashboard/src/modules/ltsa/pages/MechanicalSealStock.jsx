import { useEffect, useMemo, useState } from "react";
import { EmptyState, PageHeader, Panel } from "../../../design-system";
import { getMechanicalSealStock } from "../../../api/ai5rClient";

const PAGE_SIZE = 25;

function quantity(value) {
  return value == null ? "Unknown" : String(value);
}

export default function MechanicalSealStock() {
  const [page, setPage] = useState({ items: [], total: 0, limit: PAGE_SIZE, offset: 0 });
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState("");
  const [verificationStatus, setVerificationStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getMechanicalSealStock({ limit: PAGE_SIZE, offset: page.offset, search, verificationStatus })
      .then((result) => {
        if (active) {
          setPage(result);
          setSelected(null);
        }
      })
      .catch((reason) => {
        if (active) setError(reason?.message || "Mechanical seal stock could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [page.offset, search, verificationStatus]);

  const verifyCount = useMemo(() => page.items.filter((item) => item.verification_status !== "CONFIRMED").length, [page.items]);
  const lowCount = useMemo(() => page.items.filter((item) => item.quantity_available != null && Number(item.quantity_available) <= 0).length, [page.items]);

  function updateSearch(value) {
    setSearch(value);
    setPage((current) => ({ ...current, offset: 0 }));
  }

  function updateStatus(value) {
    setVerificationStatus(value);
    setPage((current) => ({ ...current, offset: 0 }));
  }

  return (
    <div>
      <PageHeader title="Mechanical Seal Stock" subtitle="LTSA Engineering - Complete Seal Sets" />
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
        <label>
          Search stock
          <input type="search" value={search} onChange={(event) => updateSearch(event.target.value)} />
        </label>
        <label>
          Verification
          <select value={verificationStatus} onChange={(event) => updateStatus(event.target.value)}>
            <option value="">All statuses</option>
            <option value="CONFIRMED">CONFIRMED</option>
            <option value="VERIFY">VERIFY</option>
            <option value="VERIFY_CONFIGURATION">VERIFY_CONFIGURATION</option>
            <option value="VERIFY_SIZE_COMPATIBILITY">VERIFY_SIZE_COMPATIBILITY</option>
            <option value="MASTER_LINK_VERIFY">MASTER_LINK_VERIFY</option>
            <option value="UNKNOWN">UNKNOWN</option>
          </select>
        </label>
      </div>
      <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
        <Panel><strong>Total complete seal stock</strong><div>{page.total_quantity ?? 0}</div></Panel>
        <Panel><strong>Stock pools</strong><div>{page.total}</div></Panel>
        <Panel><strong>Low stock</strong><div>{lowCount}</div></Panel>
        <Panel><strong>Verify required</strong><div>{verifyCount}</div></Panel>
      </div>
      {loading ? <Panel><p>Loading mechanical seal stock...</p></Panel> : error ? <Panel><p role="alert">{error}</p></Panel> : page.items.length === 0 ? <EmptyState title="No mechanical seal stock found" description="The stock-pool registry currently has zero matching rows." /> : (
        <>
          <Panel>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr><th>Seal Type</th><th>Size</th><th>Available Qty</th><th>Drawing / Reference</th><th>Equipment</th><th>Status</th></tr></thead>
              <tbody>{page.items.map((item) => <tr key={item.stock_pool_id} onClick={() => setSelected(item)} aria-selected={selected?.stock_pool_id === item.stock_pool_id}>
                <td>{item.seal_type}</td><td>{item.nominal_size || "Unknown"}</td><td>{quantity(item.quantity_available)}</td><td>{item.drawing_reference || "Unknown"}</td><td>{item.applications?.length ?? 0}</td><td>{item.verification_status}</td>
              </tr>)}</tbody>
            </table>
          </Panel>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16 }}>
            <span>{page.total === 0 ? "0-0 of 0" : `${page.offset + 1}-${Math.min(page.offset + page.items.length, page.total)} of ${page.total}`}</span>
            <div><button type="button" onClick={() => setPage((current) => ({ ...current, offset: Math.max(0, current.offset - PAGE_SIZE) }))} disabled={page.offset === 0}>Previous</button><button type="button" onClick={() => setPage((current) => ({ ...current, offset: current.offset + PAGE_SIZE }))} disabled={page.offset + PAGE_SIZE >= page.total}>Next</button></div>
          </div>
        </>
      )}
      {selected && <Panel><h2>Stock Detail</h2><p><strong>{selected.seal_type}</strong> {selected.nominal_size || "Unknown size"}</p><p>Physical stock size: {selected.physical_stock_size || "Unknown"}</p><p>Quantity on hand: {quantity(selected.quantity_on_hand)}</p><p>Reserved: {quantity(selected.quantity_reserved)}</p><p>Available: {quantity(selected.quantity_available)}</p><p>Location: {selected.stock_location || "Unknown"}</p><p>Reference: {selected.drawing_reference || "Unknown"}</p><p>Verification: {selected.verification_status}</p><p>Compatibility: {selected.compatibility_status}</p><p>Applicable equipment: {(selected.applications || []).map((application) => application.equipment_tag).join(", ") || "None recorded"}</p><p>Application GPNs: {(selected.applications || []).filter((application) => application.complete_seal_gpn).map((application) => `${application.equipment_tag}: ${application.complete_seal_gpn}`).join(", ") || "None recorded"}</p><h3>BOM / Components</h3><p>No BOM data available yet.</p>{selected.complete_seal_gpn != null && <p>Complete seal GPN: {selected.complete_seal_gpn}</p>}</Panel>}
    </div>
  );
}
