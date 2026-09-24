import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { IconAlert } from "./PumpWorkspaceIcons";
import { isActiveLeak, leakPresentation, leakState } from "../utils/leakSemantics";

/**
 * LTSA_CM_UI_REMEDIATION_R1D -- the one prominent Mechanical Seal Leak alert.
 *
 * Renders only for an active leak state (LEAK_DE / LEAK_NDE /
 * LEAK_DE_AND_NDE) and nothing otherwise: NO_LEAK, partial and UNKNOWN keep
 * their R1C badge/text presentation on the host surface. The state comes
 * exclusively from utils/leakSemantics -- pass the canonical `state` (e.g.
 * Current Condition's leakState) or the raw occurrence `leakDe`/`leakNde`.
 * Explicit text + icon, never colour alone; white on the danger colour.
 */
export default function MechanicalSealLeakAlert({ state, leakDe, leakNde, context }) {
  const resolved = state ?? leakState(leakDe, leakNde);
  if (!isActiveLeak(resolved)) {
    return null;
  }
  const presentation = leakPresentation(resolved);
  const headline = presentation.label.toUpperCase(); // "LEAK DETECTED — DE" etc.

  return (
    <div
      role="alert"
      data-testid="mechanical-seal-leak-alert"
      data-leak-state={presentation.state}
      data-leak-side={presentation.side}
      style={{
        display: "flex",
        alignItems: "center",
        gap: spacing.sm,
        margin: `${spacing.sm}px 0`,
        padding: `${spacing.sm}px ${spacing.md}px`,
        borderRadius: spacing.sm,
        backgroundColor: colors.danger,
        border: `2px solid ${colors.danger}`,
        color: "#FFFFFF",
      }}
    >
      <IconAlert width="22" height="22" aria-hidden="true" focusable="false" />
      <div>
        <div style={{ fontSize: "1.2rem", fontWeight: 800, letterSpacing: "0.02em", lineHeight: 1.2 }}>{headline}</div>
        <div style={{ fontSize: "0.85rem", fontWeight: 600 }}>
          Mechanical Seal Leak{context ? ` · ${context}` : ""}
        </div>
      </div>
    </div>
  );
}
