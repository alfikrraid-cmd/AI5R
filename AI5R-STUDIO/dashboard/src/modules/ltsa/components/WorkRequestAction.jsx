import { useState } from "react";
import { createWorkRequest } from "../../../api/ai5rClient";
import { useOptionalAuth } from "../auth/AuthContext";
import { can, PERMISSIONS } from "../auth/permissions";

// LTSA_PERTAMINA_WORK_REQUEST_UI_R2B -- the Asset 360 "Request Work" action.
// Submits a request record only (POST /api/ltsa/work-requests, R2); it never
// creates or changes a work order, PM/CM result or installation record.
// Each type is offered only when the session holds its request permission
// (via can(), never a role-name check); the backend stays authoritative for
// permission and asset scope. The asset tag is the page's own server-resolved
// tag, not user-editable; requester, status and time are server-set.

const REQUEST_TYPES = [
  { value: "PM", label: "Request PM", name: "PM", permission: PERMISSIONS.MAINTENANCE_REQUEST },
  { value: "CM", label: "Request CM", name: "CM", permission: PERMISSIONS.MAINTENANCE_REQUEST },
  {
    value: "INSTALLATION",
    label: "Request Installation",
    name: "Installation (Seal Installation)",
    permission: PERMISSIONS.INSTALLATION_REQUEST,
  },
];

function typeName(value) {
  return REQUEST_TYPES.find((type) => type.value === value)?.name ?? value;
}

function failureMessage(error) {
  if (error?.status === 403) return "You are not authorized to submit this request.";
  if (error?.status === 404) return "This asset was not found or is outside your access scope.";
  if (error?.status === 422) return `The request was rejected: ${error.message}`;
  if (error?.status) return `The request was not submitted (HTTP ${error.status}).`;
  return "The request could not be confirmed (network error or timeout). Check the request list before submitting again.";
}

export default function WorkRequestAction({ assetTag }) {
  const authContext = useOptionalAuth();
  const allowedTypes = REQUEST_TYPES.filter((type) => can(authContext?.session, type.permission));
  const [step, setStep] = useState("closed");
  const [requestType, setRequestType] = useState(null);
  const [description, setDescription] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (!assetTag || allowedTypes.length === 0) {
    return null;
  }

  const reset = () => {
    setStep("closed");
    setRequestType(null);
    setDescription("");
    setResult(null);
    setError(null);
  };

  const chooseType = (value) => {
    setRequestType(value);
    setError(null);
    setStep("form");
  };

  const submit = async () => {
    setStep("submitting");
    setError(null);
    try {
      const payload = await createWorkRequest({
        requestType,
        assetCode: assetTag,
        description: description.trim(),
      });
      const created = payload?.success === true ? payload.data : null;
      if (!created?.request_code) {
        setError("The server did not confirm the request. Check the request list before submitting again.");
        setStep("confirm");
        return;
      }
      setResult(created);
      setStep("done");
    } catch (err) {
      setError(failureMessage(err));
      setStep("confirm");
    }
  };

  return (
    <div className="work-request-action" data-testid="work-request-action">
      {step === "closed" ? (
        <button type="button" className="btn-link" data-testid="work-request-open" onClick={() => setStep("choose")}>
          Request Work
        </button>
      ) : null}

      {step === "choose" ? (
        <div role="group" aria-label={`Request work for ${assetTag}`} data-testid="work-request-types">
          {allowedTypes.map((type) => (
            <button
              key={type.value}
              type="button"
              className="btn-link"
              data-testid={`work-request-type-${type.value}`}
              onClick={() => chooseType(type.value)}
            >
              {type.label}
            </button>
          ))}
          <button type="button" className="btn-link" onClick={reset}>
            Cancel
          </button>
        </div>
      ) : null}

      {step === "form" ? (
        <form
          aria-label={`${typeName(requestType)} request for ${assetTag}`}
          data-testid="work-request-form"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            if (description.trim()) setStep("confirm");
          }}
        >
          <label className="part-meta" htmlFor="work-request-description">
            Description ({typeName(requestType)} · {assetTag})
          </label>
          <textarea
            id="work-request-description"
            data-testid="work-request-description"
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <button type="submit" className="btn-link" disabled={!description.trim()}>
            Review request
          </button>
          <button type="button" className="btn-link" onClick={reset}>
            Cancel
          </button>
        </form>
      ) : null}

      {step === "confirm" || step === "submitting" ? (
        <div role="dialog" aria-label="Confirm work request" data-testid="work-request-confirm">
          <p className="part-meta">
            Submit request — Asset: <b data-testid="work-request-confirm-asset">{assetTag}</b> · Type:{" "}
            <b data-testid="work-request-confirm-type">{typeName(requestType)}</b>
          </p>
          <p className="part-meta">{description.trim()}</p>
          {error ? (
            <p className="part-meta" role="alert" data-testid="work-request-error">
              {error}
            </p>
          ) : null}
          <button
            type="button"
            className="btn-link"
            data-testid="work-request-submit"
            disabled={step === "submitting"}
            onClick={submit}
          >
            {step === "submitting" ? "Submitting…" : "Confirm & submit"}
          </button>
          <button type="button" className="btn-link" disabled={step === "submitting"} onClick={() => setStep("form")}>
            Back
          </button>
          <button type="button" className="btn-link" disabled={step === "submitting"} onClick={reset}>
            Cancel
          </button>
        </div>
      ) : null}

      {step === "done" && result ? (
        <div role="status" data-testid="work-request-success">
          <p className="part-meta">
            Request <b>{result.request_code}</b> submitted — {typeName(result.request_type)} for {result.asset_code}
            {result.status ? ` (${result.status})` : ""}.
          </p>
          <button type="button" className="btn-link" onClick={reset}>
            Close
          </button>
        </div>
      ) : null}
    </div>
  );
}
