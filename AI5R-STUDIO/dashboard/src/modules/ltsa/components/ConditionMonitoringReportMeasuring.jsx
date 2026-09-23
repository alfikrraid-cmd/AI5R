import "./ConditionMonitoringReportMeasuring.css";

const dash = "—";

function numeric(value) {
  return value == null ? dash : String(value);
}

function leak(value) {
  if (value === true) return "Y";
  if (value === false) return "N";
  return dash;
}

function Pair({ label, de, nde, unit = "°C" }) {
  return (
    <tr>
      <th scope="row">{label} {unit && `(${unit})`}</th>
      <td>{numeric(de)}</td>
      <td>{numeric(nde)}</td>
    </tr>
  );
}

export default function ConditionMonitoringReportMeasuring({ reading, onClose }) {
  if (!reading) return null;

  return (
    <section className="cmon-report-measuring" data-testid="report-measuring">
      <div className="cmon-report-measuring-header">
        <div>
          <p className="eyebrow">REPORT MEASURING</p>
          <h2>Actual Measuring Report</h2>
        </div>
        <button type="button" className="workspace-quick-action-btn" onClick={onClose}>Close</button>
      </div>

      <dl className="cmon-report-measuring-identity">
        <div><dt>Date</dt><dd>{reading.readingDate ?? dash}</dd></div>
        <div><dt>Tag Number</dt><dd>{reading.equipmentTag ?? dash}</dd></div>
        <div><dt>API Plan Recorded in Source</dt><dd>{reading.apiPlanSnapshot ?? dash}</dd></div>
        <div><dt>CM Reading Code</dt><dd>{reading.id ?? dash}</dd></div>
      </dl>

      <table className="cmon-report-measuring-table">
        <thead><tr><th>Parameter</th><th>DE</th><th>NDE</th></tr></thead>
        <tbody>
          <Pair label="Flushing" de={reading.flushingTempDe} nde={reading.flushingTempNde} />
          <Pair label="Quinch" de={reading.quenchTempDe} nde={reading.quenchTempNde} />
          <Pair label="Flushing In (LBI)" de={reading.flushingInTempDe} nde={reading.flushingInTempNde} />
          <Pair label="Flushing Cut (LBO)" de={reading.flushingOutTempDe} nde={reading.flushingOutTempNde} />
          <Pair label="Cooling Water In" de={reading.coolingWaterInTempDe} nde={reading.coolingWaterInTempNde} />
          <Pair label="Cooling Water Out" de={reading.coolingWaterOutTempDe} nde={reading.coolingWaterOutTempNde} />
          <Pair label="Mechseal Temp" de={reading.mechsealTempDe} nde={reading.mechsealTempNde} />
          <Pair label="Mechanical Seal Leak" de={leak(reading.leakDe)} nde={leak(reading.leakNde)} unit="" />
          <Pair label="Water Jacket" de={reading.waterJacketTempDe} nde={reading.waterJacketTempNde} />
        </tbody>
        <tfoot>
          <tr><th>Suction (°C)</th><td colSpan="2">{numeric(reading.suctionTemp)}</td></tr>
          <tr><th>Discharge (°C)</th><td colSpan="2">{numeric(reading.dischargeTemp)}</td></tr>
          <tr><th>Status</th><td colSpan="2">{reading.pumpOperatingState ?? dash}</td></tr>
        </tfoot>
      </table>

      <div className="cmon-report-measuring-finding">
        <h3>Finding</h3>
        <p>{reading.finding ?? dash}</p>
      </div>
    </section>
  );
}
