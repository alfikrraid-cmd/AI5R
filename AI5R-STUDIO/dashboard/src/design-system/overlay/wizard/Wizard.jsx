import { useState } from "react";

export default function Wizard({ steps = [], onClose, onComplete }) {
    const [stepIndex, setStepIndex] = useState(0);

    const step = steps[stepIndex];
    const isFirst = stepIndex === 0;
    const isLast = stepIndex === steps.length - 1;

    function handleBack() {
        setStepIndex((index) => Math.max(0, index - 1));
    }

    function handleNext() {
        if (isLast) {
            onComplete?.();
            return;
        }

        setStepIndex((index) => Math.min(steps.length - 1, index + 1));
    }

    return (
        <div
            style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
            }}
        >
            <div
                style={{
                    pointerEvents: "auto",
                    width: 480,
                    maxWidth: "90vw",
                    background: "#0F172A",
                    border: "1px solid #1E293B",
                    borderRadius: 16,
                    boxShadow: "0 20px 60px rgba(0,0,0,.5)",
                    display: "flex",
                    flexDirection: "column",
                }}
            >
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "16px 20px",
                        borderBottom: "1px solid #1E293B",
                    }}
                >
                    <div
                        style={{
                            fontSize: 16,
                            fontWeight: 700,
                            color: "#F1F5F9",
                        }}
                    >
                        {step?.title}
                    </div>

                    <div style={{ fontSize: 12, color: "#64748B" }}>
                        Step {stepIndex + 1} of {steps.length}
                    </div>
                </div>

                <div style={{ padding: 20, color: "#F1F5F9" }}>
                    {step?.content}
                </div>

                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "12px 20px",
                        borderTop: "1px solid #1E293B",
                    }}
                >
                    <button
                        type="button"
                        onClick={onClose}
                        style={{
                            background: "transparent",
                            border: "none",
                            color: "#64748B",
                            cursor: "pointer",
                            fontSize: 13,
                        }}
                    >
                        Cancel
                    </button>

                    <div style={{ display: "flex", gap: 8 }}>
                        {!isFirst && (
                            <button
                                type="button"
                                onClick={handleBack}
                                style={{
                                    background: "transparent",
                                    border: "1px solid #1E293B",
                                    borderRadius: 8,
                                    color: "#F1F5F9",
                                    padding: "6px 14px",
                                    fontSize: 13,
                                    cursor: "pointer",
                                }}
                            >
                                Back
                            </button>
                        )}

                        <button
                            type="button"
                            onClick={handleNext}
                            style={{
                                background: "#2563EB",
                                border: "none",
                                borderRadius: 8,
                                color: "#FFFFFF",
                                padding: "6px 14px",
                                fontSize: 13,
                                cursor: "pointer",
                            }}
                        >
                            {isLast ? "Finish" : "Next"}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
