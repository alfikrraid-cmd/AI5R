import { useEffect, useRef, useState } from "react";
import { Badge, Button } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { getPMCMEvidence, pmCMEvidenceDownloadUrl, uploadPMCMEvidence } from "../../../api/ai5rClient";

// MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 2 -- the ONE canonical evidence
// attachment widget for both PM Occurrence and Condition Monitoring
// Reading detail views (no duplicate upload implementation). Backed
// entirely by the already-real pm_cm_evidence contract (uploadPMCMEvidence/
// getPMCMEvidence/pmCMEvidenceDownloadUrl, ai5rClient.js) -- no second
// storage mechanism, no client-only fallback.
export const EVIDENCE_RECORD_TYPES = Object.freeze({
  PM_OCCURRENCE: "PM_OCCURRENCE",
  CONDITION_MONITORING_READING: "CONDITION_MONITORING_READING",
});

// Matches pm_cm_evidence_repository.py's ALLOWED_CATEGORIES/
// ALLOWED_CONTENT_TYPES exactly (this session's own re-read of that
// file) -- never a client-invented category or extension.
const CATEGORY_OPTIONS = ["PHOTO", "REPORT", "MEASUREMENT", "OTHER"];
const ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".pdf"];

function formatFileSize(bytes) {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function EvidenceAttachments({ recordType, recordCode, canUpload }) {
  const [evidence, setEvidence] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [category, setCategory] = useState("PHOTO");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const inputRef = useRef(null);

  function load() {
    if (!recordCode) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setLoadError(null);
    getPMCMEvidence(recordType, recordCode)
      .then((list) => setEvidence(list))
      .catch(() => setLoadError("Unable to load evidence."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordType, recordCode]);

  async function handleFileSelected(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);
    try {
      const result = await uploadPMCMEvidence({ recordType, recordCode, category, file });
      // Reload persistence proof, not a locally-fabricated row: the newly
      // created evidence record comes back from the real POST response
      // (result.data), the same shape getPMCMEvidence() returns on a
      // fresh GET -- this widget never renders a client-only placeholder
      // as if it were successfully persisted.
      setEvidence((current) => [...current, result.data]);
      setUploadSuccess(`${file.name} uploaded.`);
    } catch (err) {
      // Never fake a successful upload -- surface the verbatim backend/
      // client error (e.g. an unsupported content type or the 15MB cap
      // enforced by validate_upload()).
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      {canUpload && (
        <div
          style={{
            display: "flex",
            gap: spacing.sm,
            alignItems: "center",
            marginBottom: spacing.sm,
            flexWrap: "wrap",
          }}
        >
          <select
            aria-label="Evidence category"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            disabled={uploading}
          >
            {CATEGORY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <Button onClick={() => inputRef.current?.click()} disabled={uploading || !recordCode}>
            {uploading ? "Uploading..." : "Upload Photo / PDF"}
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS.join(",")}
            style={{ display: "none" }}
            onChange={handleFileSelected}
            data-testid="evidence-file-input"
          />
        </div>
      )}

      {uploadError && (
        <p role="alert" data-testid="evidence-upload-error" style={{ color: colors.danger }}>
          {uploadError}
        </p>
      )}
      {uploadSuccess && (
        <p role="status" data-testid="evidence-upload-success" style={{ color: colors.success }}>
          {uploadSuccess}
        </p>
      )}

      {loading ? (
        <p style={{ color: colors.textMuted }}>Loading evidence...</p>
      ) : loadError ? (
        <div>
          <p role="alert">{loadError}</p>
          <Button onClick={load}>Retry</Button>
        </div>
      ) : evidence.length === 0 ? (
        <p style={{ color: colors.textMuted }}>No evidence attached.</p>
      ) : (
        <ul style={{ listStyle: "none", margin: 0, padding: 0 }} data-testid="evidence-list">
          {evidence.map((item) => (
            <li
              key={item.evidence_id}
              style={{ padding: `${spacing.xs}px 0`, borderBottom: `1px solid ${colors.border}` }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: spacing.xs,
                }}
              >
                <a href={pmCMEvidenceDownloadUrl(item.evidence_id)} target="_blank" rel="noreferrer">
                  {item.file_name}
                </a>
                <Badge variant="info">{item.category ?? "OTHER"}</Badge>
              </div>
              {/* Attribution/provenance (Phase 12): uploaded_by is a raw
                  actor UUID -- no display-name resolution exists anywhere
                  in this codebase and this MWO forbids building one just
                  to prettify names, so the honest identifier is shown as-is. */}
              <div style={{ color: colors.textMuted, fontSize: 12 }}>
                {item.content_type} · {formatFileSize(item.file_size_bytes)} · {item.uploaded_at ?? "—"}
                {item.uploaded_by ? ` · Uploaded by ${item.uploaded_by}` : ""}
                {item.source ? ` · ${item.source}` : ""}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
