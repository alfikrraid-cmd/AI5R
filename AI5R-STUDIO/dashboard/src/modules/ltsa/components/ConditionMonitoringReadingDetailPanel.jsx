import { Badge, Button, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

function tempValue(value) {
  return value != null ? `${value} °C` : "—";
}

export default function ConditionMonitoringReadingDetailPanel({
  reading,
  onViewAsset360,
  onViewSchedule,
}) {
  if (!reading) {
    return (
      <EmptyState
        title="No Condition Monitoring reading selected"
        description="Select a reading from the list to view its details."
      />
    );
  }

  const leakDetected = reading.leakDe || reading.leakNde;

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>{reading.id}</h2>

      <Card title="Reading Summary">
        <Field
          label="Equipment"
          value={reading.area ? `${reading.equipmentTag} — ${reading.area}` : reading.equipmentTag}
        />
        <Field label="Reading Date" value={reading.readingDate ?? "—"} />
        <Field label="Pump Operating State" value={reading.pumpOperatingState ?? "Not recorded"} />

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Seal Leak</div>
          <Badge variant={leakDetected ? "danger" : "success"}>
            {leakDetected ? "Leak detected" : "No leak"}
          </Badge>
        </div>
      </Card>

      <Card title="Temperatures (DE / NDE)">
        <Field
          label="Flushing"
          value={`${tempValue(reading.flushingTempDe)} / ${tempValue(reading.flushingTempNde)}`}
        />
        <Field
          label="Quench"
          value={`${tempValue(reading.quenchTempDe)} / ${tempValue(reading.quenchTempNde)}`}
        />
        <Field
          label="Flushing In (LBI)"
          value={`${tempValue(reading.flushingInTempDe)} / ${tempValue(reading.flushingInTempNde)}`}
        />
        <Field
          label="Flushing Out (LBO)"
          value={`${tempValue(reading.flushingOutTempDe)} / ${tempValue(reading.flushingOutTempNde)}`}
        />
        <Field
          label="Cooling Water In"
          value={`${tempValue(reading.coolingWaterInTempDe)} / ${tempValue(reading.coolingWaterInTempNde)}`}
        />
        <Field
          label="Cooling Water Out"
          value={`${tempValue(reading.coolingWaterOutTempDe)} / ${tempValue(reading.coolingWaterOutTempNde)}`}
        />
        <Field
          label="Mechseal"
          value={`${tempValue(reading.mechsealTempDe)} / ${tempValue(reading.mechsealTempNde)}`}
        />
        <Field
          label="Water Jacket"
          value={`${tempValue(reading.waterJacketTempDe)} / ${tempValue(reading.waterJacketTempNde)}`}
        />
        <Field label="Suction" value={tempValue(reading.suctionTemp)} />
        <Field label="Discharge" value={tempValue(reading.dischargeTemp)} />
      </Card>

      <Card title="Related Schedule">
        {reading.scheduleCode ? (
          <Button onClick={() => onViewSchedule?.(reading.scheduleCode)}>{reading.scheduleCode}</Button>
        ) : (
          <div style={{ color: colors.textMuted }}>No owning schedule recorded.</div>
        )}
      </Card>

      <Card title="Quick Actions">
        <Button onClick={() => onViewAsset360?.(reading.equipmentTag)}>View Asset 360</Button>
      </Card>
    </div>
  );
}
