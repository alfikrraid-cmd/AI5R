/**
 * Icons ported 1:1 from DESIGN/LTSA/PUMP_WORKSPACE/pump-workspace.html
 * ("1.6px monoline, currentColor"). No icon library dependency added --
 * the design's own inline SVGs, unchanged.
 */
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

export const IconWrench = (props) => (
  <Icon {...props}>
    <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2-2z" />
  </Icon>
);

export const IconHistory = (props) => (
  <Icon {...props}>
    <path d="M3 12a9 9 0 1 0 3-6.7" />
    <path d="M3 3v5h5" />
    <path d="M12 7v5l3 3" />
  </Icon>
);

export const IconDrawing = (props) => (
  <Icon {...props}>
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <path d="M8 8h8M8 12h8M8 16h5" />
  </Icon>
);

export const IconBox = (props) => (
  <Icon {...props}>
    <path d="M21 8 12 3 3 8v8l9 5 9-5z" />
    <path d="M3 8l9 5 9-5" />
    <path d="M12 13v8" />
  </Icon>
);

export const IconAlert = (props) => (
  <Icon {...props}>
    <path d="M12 3 2 20h20L12 3z" />
    <path d="M12 10v4" />
    <path d="M12 17h.01" />
  </Icon>
);

export const IconSun = (props) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </Icon>
);

export const IconMoon = (props) => (
  <Icon {...props}>
    <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
  </Icon>
);

export const IconClose = (props) => (
  <Icon {...props}>
    <path d="M18 6 6 18M6 6l12 12" />
  </Icon>
);

export const IconCheck = (props) => (
  <Icon {...props}>
    <path d="M20 6 9 17l-5-5" />
  </Icon>
);

export const IconSearch = (props) => (
  <Icon {...props}>
    <circle cx="11" cy="11" r="7" />
    <path d="m21 21-4.35-4.35" />
  </Icon>
);

export const IconShield = (props) => (
  <Icon {...props}>
    <path d="M12 3l7 3v6c0 4.4-3 7.6-7 9-4-1.4-7-4.6-7-9V6z" />
    <path d="m9.5 12 1.8 1.8L15 10" />
  </Icon>
);

export const IconClipboard = (props) => (
  <Icon {...props}>
    <rect x="6" y="4" width="12" height="17" rx="2" />
    <path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1" />
    <path d="M9 10h6M9 14h6M9 18h4" />
  </Icon>
);

export const IconCamera = (props) => (
  <Icon {...props}>
    <path d="M4 8h3l1.5-2h7L17 8h3v11H4z" />
    <circle cx="12" cy="13.5" r="3.3" />
  </Icon>
);

export const IconPaperclip = (props) => (
  <Icon {...props}>
    <path d="M19.5 12.5 12 20a4.5 4.5 0 0 1-6.4-6.4L13 6.2a3 3 0 0 1 4.3 4.3L10 17.8a1.5 1.5 0 0 1-2.1-2.1l6.7-6.7" />
  </Icon>
);

export const IconPen = (props) => (
  <Icon {...props}>
    <path d="m17 3 4 4L9 19l-4.5 1.5L6 16z" />
  </Icon>
);

export const IconDownload = (props) => (
  <Icon {...props}>
    <path d="M12 3v12m0 0-4-4m4 4 4-4" />
    <path d="M4 18v2a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-2" />
  </Icon>
);

const TIER_ICON = {
  pm: IconCheck,
  cm: IconWrench,
  breakdown: IconAlert,
  alert: IconAlert,
};

export function TierIcon({ tier, ...props }) {
  const Component = TIER_ICON[tier] ?? IconAlert;
  return <Component {...props} />;
}
