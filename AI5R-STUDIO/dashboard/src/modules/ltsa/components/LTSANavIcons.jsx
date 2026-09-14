/**
 * UI-D1.2 -- small monoline nav icons for LTSASidebar, matching Chief's
 * reference (compact icon + label rows). Same inline-SVG convention
 * PumpWorkspaceIcons.jsx already established (no icon library dependency
 * added) -- reuses that file's icons directly where a fit already exists
 * (Wrench/Clipboard/Box/Alert/History) and adds only the handful this
 * sidebar needs that file doesn't have (Dashboard grid, Seal ring,
 * Pulse/Condition, Book/Knowledge, Sparkle/AI, Layers/Asset360).
 */
import {
  IconWrench,
  IconClipboard,
  IconBox,
  IconAlert,
  IconHistory,
  IconDownload,
} from "./PumpWorkspaceIcons";

function Icon({ children, ...props }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {children}
    </svg>
  );
}

export const IconDashboard = (props) => (
  <Icon {...props}>
    <rect x="3" y="3" width="7" height="7" rx="1.5" />
    <rect x="14" y="3" width="7" height="7" rx="1.5" />
    <rect x="3" y="14" width="7" height="7" rx="1.5" />
    <rect x="14" y="14" width="7" height="7" rx="1.5" />
  </Icon>
);

export const IconSeal = (props) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="8" />
    <circle cx="12" cy="12" r="3" />
  </Icon>
);

export const IconPulse = (props) => (
  <Icon {...props}>
    <path d="M3 12h4l2-7 4 14 2-7h6" />
  </Icon>
);

export const IconBook = (props) => (
  <Icon {...props}>
    <path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v17H6.5A2.5 2.5 0 0 0 4 21.5v-17z" />
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
  </Icon>
);

export const IconSparkle = (props) => (
  <Icon {...props}>
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />
  </Icon>
);

export const IconLayers = (props) => (
  <Icon {...props}>
    <path d="M12 3 2 8l10 5 10-5-10-5z" />
    <path d="M2 13l10 5 10-5" />
  </Icon>
);

export const IconBell = (props) => (
  <Icon {...props}>
    <path d="M6 10a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 14 6 10z" />
    <path d="M10 19a2 2 0 0 0 4 0" />
  </Icon>
);

export const IconUser = (props) => (
  <Icon {...props}>
    <circle cx="12" cy="8" r="3.5" />
    <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
  </Icon>
);

export const IconMore = (props) => (
  <Icon {...props}>
    <circle cx="5" cy="12" r="1.4" fill="currentColor" stroke="none" />
    <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
    <circle cx="19" cy="12" r="1.4" fill="currentColor" stroke="none" />
  </Icon>
);

// Nav key -> icon component, covering every LTSAWorkspace TABS key this
// sidebar renders (primary + "More"). A key with no entry here (should
// not happen -- every key below is verified against LTSAWorkspace.jsx's
// own TABS list) falls back to IconMore in LTSASidebar.jsx, never a
// broken import.
export const NAV_ICONS = {
  dashboard: IconDashboard,
  pump: IconWrench,
  seal: IconSeal,
  workorder: IconClipboard,
  pm: IconClipboard,
  cm: IconWrench,
  cmon: IconPulse,
  failure: IconAlert,
  inventory: IconBox,
  knowledge: IconBook,
  "ai-insight": IconSparkle,
  history: IconLayers,
  drawing: IconBox,
  document: IconBook,
  installation: IconClipboard,
  knowledgereview: IconBook,
  import: IconDownload,
  reports: IconClipboard,
  analytics: IconPulse,
  "historical-review": IconHistory,
  "historical-batch-review": IconHistory,
  "whatsapp-groups": IconUser,
};
