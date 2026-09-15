/**
 * AI5R Design System — color tokens.
 * Single source of truth for every color used by src/design-system/*.
 * background/panel match the pre-existing dashboard theme (src/index.css
 * body/.card) exactly, so migrating consumers onto these tokens changes
 * no visuals.
 *
 * MWO-LTSA-LIGHT-THEME-CONTRAST-FIX -- every value is now
 * `var(--ltsa-<token>, <original dark value>)` instead of a bare hex.
 * This is the ONE shared/root fix for the reported bug (PageHeader's
 * title/subtitle, Card, Table, and every other design-system component
 * apply these via plain inline styles, e.g. `color: colors.text` --
 * none of them need to change individually): CSS var() falls back to
 * the fallback argument only when the custom property is undefined in
 * the cascade. Inside `.ltsa-shell` (ltsaTokens.css, UI-D1.2, already
 * wraps every LTSA workspace via LTSAWorkspace.jsx's own root render)
 * the real --ltsa-text/--ltsa-surface/etc. values apply, fixing the
 * white-on-white contrast. Everywhere this design-system is ALSO used
 * (the "od" module's AgentOps/CommandCenter console, per ltsaTokens.css's
 * own header comment) --ltsa-* is simply undefined, so every value
 * resolves to the exact same original dark hex as before -- zero visual
 * change there, not touched, not risked.
 */
const colors = {
  background: "var(--ltsa-bg, #0B1020)",
  panel: "var(--ltsa-surface, #151C33)",
  border: "var(--ltsa-border, #1F2937)",
  text: "var(--ltsa-text, #FFFFFF)",
  textMuted: "var(--ltsa-text-muted, #94A3B8)",
  success: "var(--ltsa-success, #22C55E)",
  info: "var(--ltsa-info, #3B82F6)",
  warning: "var(--ltsa-warning, #F59E0B)",
  danger: "var(--ltsa-danger, #EF4444)",
  purple: "#8B5CF6",
};

export default colors;
