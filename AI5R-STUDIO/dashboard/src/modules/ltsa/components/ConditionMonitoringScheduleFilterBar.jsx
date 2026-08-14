import { SearchBox } from "../../../design-system";
import spacing from "../../../design-system/theme/spacing";

export default function ConditionMonitoringScheduleFilterBar({ searchValue, onSearchChange }) {
  return (
    <div style={{ marginBottom: spacing.md }}>
      <SearchBox
        value={searchValue}
        onChange={onSearchChange}
        placeholder="Search by schedule ID or equipment tag..."
      />
    </div>
  );
}
