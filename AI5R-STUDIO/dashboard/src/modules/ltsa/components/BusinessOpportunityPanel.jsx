import { Card, EmptyState } from "../../../design-system";

/**
 * RC-002 (Executive Dashboard React Implementation). Placeholder only, per
 * mission instruction ("No fake calculations") -- no cost-savings, ROI, or
 * revenue estimate is computed anywhere in this file.
 */
export default function BusinessOpportunityPanel() {
  return (
    <Card title="Business Opportunity">
      <EmptyState
        title="Business Opportunity analysis is not yet available"
        description="No cost, savings, or revenue calculation exists yet — reserved for a future, separately-scoped analytics capability."
      />
    </Card>
  );
}
