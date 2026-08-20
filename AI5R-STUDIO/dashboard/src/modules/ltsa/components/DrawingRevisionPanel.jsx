import { Badge, Button, Card, EmptyState, Table } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

/**
 * Revision History / Revision Timeline. Foundation scope
 * (drawing-workspace-spec.html §09 RevisionHistoryTimeline) extended in
 * place for RC-003B §6 (Author, Checker columns added) rather than built
 * as a second, parallel "Revision Timeline" component -- RC-003B
 * explicitly forbids a duplicate Revision Panel, and this same Table
 * already carries every field RC-003B asks for (Revision/Date/Author/
 * Checker/Approver/Description/Current). Reuses the design-system Table
 * (already used by PumpDetailPanel/WorkOrderDetailPanel for row lists).
 * "Open Revision" is a real, working interaction (updates
 * `openedRevision`, shown as feedback text) -- not a fabricated no-op.
 */
export default function DrawingRevisionPanel({ drawing, openedRevision, onOpenRevision }) {
  if (!drawing) {
    return (
      <Card title="Revision History">
        <EmptyState
          title="No revision history to show"
          description="Revision history appears here once a drawing is opened."
        />
      </Card>
    );
  }

  return (
    <Card title="Revision History">
      {openedRevision ? (
        <p style={{ color: colors.textMuted, marginBottom: spacing.sm }}>
          Viewing Rev {openedRevision}
          {openedRevision !== drawing.currentRevision ? " — not current" : ""}
        </p>
      ) : null}

      <Table
        rowKey="revision"
        data={drawing.revisions}
        columns={[
          { key: "revision", header: "Revision" },
          { key: "date", header: "Date" },
          { key: "author", header: "Author", render: (value) => value ?? "Unavailable" },
          { key: "checker", header: "Checker", render: (value) => value ?? "Unavailable" },
          { key: "approvedBy", header: "Approver", render: (value) => value ?? "Unavailable" },
          { key: "description", header: "Description" },
          {
            key: "approvalStatus",
            header: "Approval",
            render: (value) => (
              <Badge variant={value === "APPROVED" ? "success" : "warning"}>{value}</Badge>
            ),
          },
          {
            key: "current",
            header: "Status",
            render: (value, row) =>
              value ? (
                <Badge variant="info">Current</Badge>
              ) : row.obsolete ? (
                <Badge variant="danger">Obsolete</Badge>
              ) : (
                "—"
              ),
          },
          {
            key: "action",
            header: "",
            render: (_value, row) => (
              <Button onClick={() => onOpenRevision(row.revision)}>Open Revision</Button>
            ),
          },
        ]}
      />
    </Card>
  );
}
