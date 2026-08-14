import { Card, EmptyState, Table } from "../../../design-system";

/**
 * RC-002 (Executive Dashboard React Implementation): "Assets Requiring
 * Immediate Action". Reuses the exact same `assets` data AttentionAssetList
 * already renders (buildAttentionAssets(), computed once in
 * ExecutiveDashboard.jsx and passed to both) -- no second filtering rule,
 * no duplicate KPI/business logic. Only the presentation differs: a table,
 * distinct from AttentionAssetList's card-list, so the two are not the
 * same widget rendered twice.
 */
export default function ImmediateActionTable({ assets }) {
  if (assets.length === 0) {
    return (
      <Card title="Assets Requiring Immediate Action">
        <EmptyState
          title="No assets currently require immediate action"
          description="Every high-criticality asset is running normally with no open work."
        />
      </Card>
    );
  }

  return (
    <Card title="Assets Requiring Immediate Action">
      <Table
        rowKey="tag"
        data={assets}
        columns={[
          { key: "pump", header: "Asset" },
          { key: "tag", header: "Tag" },
          { key: "criticality", header: "Criticality" },
          { key: "status", header: "Status" },
          { key: "openWorkOrders", header: "Open Work Orders" },
        ]}
      />
    </Card>
  );
}
