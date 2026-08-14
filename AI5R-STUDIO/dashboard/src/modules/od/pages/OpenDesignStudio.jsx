import { useState } from "react";
import { Button, Card, PageHeader, ProgressBar } from "../../../design-system";
import guidedElaborationSteps from "../data/guidedElaborationSteps";
import buildBusinessBlueprint from "../utils/blueprintBuilder";
import "./OpenDesignStudio.css";

const TOTAL_STEPS = 1 + guidedElaborationSteps.length + 1;

/**
 * Open Design's capture flow (OD-001): one Mission Input, a small fixed
 * number of Guided Elaboration steps (one question per screen), then a
 * Review before sealing the mock Business Blueprint. No backend — the
 * sealed blueprint is handed to the caller via onComplete.
 */
export default function OpenDesignStudio({ onComplete }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [missionInput, setMissionInput] = useState("");
  const [answers, setAnswers] = useState({});
  const [draft, setDraft] = useState("");

  const isMissionInputStep = stepIndex === 0;
  const elaborationStep =
    stepIndex >= 1 && stepIndex <= guidedElaborationSteps.length
      ? guidedElaborationSteps[stepIndex - 1]
      : null;
  const isReviewStep = stepIndex === guidedElaborationSteps.length + 1;

  function handleMissionInputContinue() {
    setMissionInput(draft);
    setDraft("");
    setStepIndex(1);
  }

  function handleElaborationContinue() {
    setAnswers((previous) => ({ ...previous, [elaborationStep.key]: draft }));
    setDraft("");
    setStepIndex((previous) => previous + 1);
  }

  function handleSeal() {
    onComplete(buildBusinessBlueprint({ missionInput, answers }));
  }

  return (
    <div className="od-studio">
      <PageHeader title="Open Design" subtitle="Let's turn your ask into a Business Blueprint." />

      <ProgressBar
        value={stepIndex}
        max={TOTAL_STEPS - 1}
        label={`Step ${stepIndex + 1} of ${TOTAL_STEPS}`}
      />

      {isMissionInputStep ? (
        <Card title="What do you want your AI Company to do for you?">
          <textarea
            aria-label="Mission Input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows={4}
            className="od-studio-field"
          />
          <Button onClick={handleMissionInputContinue} disabled={!draft.trim()}>
            Continue
          </Button>
        </Card>
      ) : null}

      {elaborationStep ? (
        <Card title={elaborationStep.question}>
          <input
            aria-label={elaborationStep.question}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={elaborationStep.placeholder}
            className="od-studio-field"
          />
          <Button onClick={handleElaborationContinue} disabled={!draft.trim()}>
            Continue
          </Button>
        </Card>
      ) : null}

      {isReviewStep ? (
        <Card title="Review">
          <p>
            <strong>Your ask:</strong> {missionInput}
          </p>

          {guidedElaborationSteps.map((step) => (
            <p key={step.key}>
              <strong>{step.question}</strong> {answers[step.key]}
            </p>
          ))}

          <Button onClick={handleSeal}>Confirm &amp; Seal Blueprint</Button>
        </Card>
      ) : null}
    </div>
  );
}
