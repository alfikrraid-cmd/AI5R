import { getWorkOrderAsset } from "../../../api/ai5rClient";

/**
 * API-to-Registry field mapping (APP-006, per ADR-WO-002/ADR-WO-003):
 * work_order_code -> id, asset_code -> equipmentTag, work_type -> workType,
 * assigned_to -> assignedTechnician, due_date -> dueDate,
 * created_at -> createdDate. area and timeline are deliberately left
 * unset here -- both are derived via separate API calls
 * (getWorkOrderAsset / getWorkOrderTimeline), never fabricated.
 * requestedBy is intentionally never set (ADR-WO-003: remains optional,
 * not implemented this sprint).
 */

function formatDateOnly(value) {
  if (!value) {
    return null;
  }

  return String(value).slice(0, 10);
}

export function mapWorkOrderRecord(record) {
  return {
    id: record.work_order_code,
    title: record.title,
    equipmentTag: record.asset_code,
    area: null,
    workType: record.work_type,
    priority: record.priority,
    assignedTechnician: record.assigned_to,
    dueDate: formatDateOnly(record.due_date),
    status: record.status,
    createdDate: formatDateOnly(record.created_at),
    description: record.description,
    timeline: [],
  };
}

export function mapTimelineRecord(record) {
  return {
    date: formatDateOnly(record.performed_at),
    event: record.action_taken,
  };
}

function emptyToNull(value) {
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

/**
 * CreateWorkOrderModal form -> POST /api/ltsa/workorders payload (APP-008).
 * `area` is deliberately dropped: per ADR-WO-002/ADR-WO-003 it is Asset
 * data, not Work Order data, and the canonical create contract
 * (WorkOrderCreateRequest) has no field for it -- sending it would either
 * be silently ignored or fabricate a value the schema was never given a
 * home for. `customer_code`/`asset_type`/`status` are omitted: the form
 * (frozen, not modified by this MWO) has no corresponding fields, and
 * `status` already defaults to "OPEN" server-side.
 */
export function mapFormToCreatePayload(form, workOrderCode) {
  return {
    work_order_code: workOrderCode,
    description: form.description,
    asset_code: emptyToNull(form.equipmentTag),
    priority: emptyToNull(form.priority),
    assigned_to: emptyToNull(form.assignedTechnician),
    title: emptyToNull(form.title),
    work_type: emptyToNull(form.workType),
    due_date: emptyToNull(form.dueDate),
  };
}

/**
 * Resolves `area` from the Asset API (WO-BE-003) for one already-mapped
 * work order. Never throws -- an unresolved asset (unsupported asset_type,
 * unknown asset, or a network failure) leaves `area: null`, the same
 * "honestly absent, never fabricated" convention as the rest of this
 * mapping, rather than failing the whole list for one row.
 */
export async function withResolvedArea(workOrder) {
  try {
    const asset = await getWorkOrderAsset(workOrder.id);
    return { ...workOrder, area: asset?.area ?? null };
  } catch {
    return workOrder;
  }
}
