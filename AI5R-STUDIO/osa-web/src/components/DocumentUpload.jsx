import { useRef, useState } from "react";

// Studio is a presentation-only client of LTSA-BRAIN's n8n workflows -- no
// business logic, validation rules, OCR, or extraction happens here. This
// component only collects a file, uploads it to the LTSA Document Upload
// webhook, and renders whatever that workflow returns.
const LTSA_API_BASE = import.meta.env.VITE_LTSA_API_BASE || "http://localhost:5678";
const ALLOWED_TYPES = ["application/pdf", "image/jpeg", "image/jpg", "image/png"];

function uploadDocument({ file, knowledgeSourceId, sourceDocumentId, documentFieldExtractionId }, onProgress) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("data", file);
    formData.append("knowledge_source_id", knowledgeSourceId);
    formData.append("source_document_id", sourceDocumentId);
    formData.append("document_field_extraction_id", documentFieldExtractionId);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${LTSA_API_BASE}/webhook/ltsa/document/upload`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300 && body.success) {
          resolve(body.data);
        } else {
          reject(new Error(body.message || `Upload failed (HTTP ${xhr.status})`));
        }
      } catch {
        reject(new Error(`Upload failed (HTTP ${xhr.status})`));
      }
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));

    xhr.send(formData);
  });
}

function DocumentUpload({ onExtracted }) {
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  async function handleFile(file) {
    setError(null);

    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Unsupported file type. Please upload a PDF, JPG, JPEG, or PNG.");
      return;
    }

    setProgress(0);
    try {
      const result = await uploadDocument(
        {
          file,
          knowledgeSourceId: crypto.randomUUID(),
          sourceDocumentId: crypto.randomUUID(),
          documentFieldExtractionId: crypto.randomUUID(),
        },
        setProgress
      );
      onExtracted(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setProgress(null);
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragActive(false);
    const file = event.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  function handleFilePicked(event) {
    const file = event.target.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div className="document-upload">
      <h2>Upload Engineering Document</h2>

      <div
        className={`document-upload__dropzone${dragActive ? " document-upload__dropzone--active" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <p>Drag &amp; drop a document here, or click to choose a file</p>
        <p className="document-upload__hint">PDF, JPG, JPEG, PNG</p>
        <input
          ref={fileInputRef}
          type="file"
          accept={ALLOWED_TYPES.join(",")}
          style={{ display: "none" }}
          onChange={handleFilePicked}
        />
      </div>

      {progress !== null && (
        <div className="document-upload__progress">
          <div className="document-upload__progress-bar" style={{ width: `${progress}%` }} />
          <span>{progress}%</span>
        </div>
      )}

      {error && <p className="document-upload__error">{error}</p>}
    </div>
  );
}

export default DocumentUpload;
