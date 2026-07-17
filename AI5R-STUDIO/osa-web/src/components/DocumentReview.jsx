import { useState } from "react";

// Presentation-only: renders whatever the LTSA Upload webhook returned,
// lets the engineer edit values, and posts the edited set to the LTSA Save
// webhook. No matching/registry logic happens here -- that is performed by
// the LTSA workflow (WF-LTSA-DOCUMENT-SAVE-001) after Save is clicked.
const LTSA_API_BASE = import.meta.env.VITE_LTSA_API_BASE || "http://localhost:5678";
const LOW_CONFIDENCE_THRESHOLD = 0.7;

const FIELD_GROUPS = [
  {
    label: "General",
    fields: [
      ["customer", "Customer"],
      ["end_user", "End User"],
      ["date", "Date"],
      ["location", "Location"],
    ],
  },
  {
    label: "Pump",
    fields: [
      ["pump_manufacturer", "Manufacturer"],
      ["pump_model", "Model"],
      ["pump_size", "Size"],
      ["pump_speed", "Speed"],
      ["pump_rotation", "Rotation"],
      ["pump_equipment_number", "Equipment Number"],
    ],
  },
  {
    label: "Mechanical Seal",
    fields: [
      ["seal_manufacturer", "Manufacturer"],
      ["seal_type", "Seal Type"],
      ["seal_drawing_number", "Drawing Number"],
      ["seal_material_code", "Material Code"],
      ["seal_api_plan", "API Plan"],
      ["seal_location", "Seal Location"],
    ],
  },
  {
    label: "Process",
    fields: [
      ["process_liquid", "Liquid"],
      ["process_temperature", "Temperature"],
      ["process_pressure", "Pressure"],
      ["process_specific_gravity", "Specific Gravity"],
      ["process_viscosity", "Viscosity"],
    ],
  },
];

function saveDocument(documentFieldExtractionId, reviewedFields) {
  return fetch(`${LTSA_API_BASE}/webhook/ltsa/document/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      document_field_extraction_id: documentFieldExtractionId,
      reviewed_fields: reviewedFields,
    }),
  }).then(async (response) => {
    const body = await response.json();
    if (!response.ok || !body.success) {
      throw new Error(body.message || `Save failed (HTTP ${response.status})`);
    }
    return body.data;
  });
}

function DocumentReview({ extraction, onSaved }) {
  const [fields, setFields] = useState(extraction.extracted_fields || {});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  function updateValue(name, value) {
    setFields((prev) => ({ ...prev, [name]: { ...prev[name], value } }));
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await saveDocument(extraction.document_field_extraction_id, fields);
      setSaved(true);
      onSaved?.(fields);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="document-review">
      <h2>Review Extracted Fields</h2>
      <p className="document-review__doc-type">
        Detected document type: <strong>{extraction.detected_document_type}</strong>
        {extraction.detected_document_type_confidence != null && (
          <span> ({Math.round(extraction.detected_document_type_confidence * 100)}% confidence)</span>
        )}
      </p>

      {FIELD_GROUPS.map((group) => (
        <fieldset key={group.label} className="document-review__group">
          <legend>{group.label}</legend>
          {group.fields.map(([name, label]) => {
            const entry = fields[name] || {};
            const lowConfidence =
              entry.confidence != null && entry.confidence < LOW_CONFIDENCE_THRESHOLD;

            return (
              <label
                key={name}
                className={`document-review__field${lowConfidence ? " document-review__field--low-confidence" : ""}`}
              >
                <span>{label}</span>
                <input
                  type="text"
                  value={entry.value ?? ""}
                  onChange={(event) => updateValue(name, event.target.value)}
                />
                {entry.confidence != null && (
                  <span className="document-review__confidence">
                    {Math.round(entry.confidence * 100)}%
                  </span>
                )}
              </label>
            );
          })}
        </fieldset>
      ))}

      <button onClick={handleSave} disabled={saving || saved}>
        {saved ? "Saved" : saving ? "Saving..." : "Save"}
      </button>

      {error && <p className="document-review__error">{error}</p>}
    </div>
  );
}

export default DocumentReview;
