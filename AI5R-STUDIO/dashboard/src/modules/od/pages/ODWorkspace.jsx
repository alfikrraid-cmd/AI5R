import { useState } from "react";
import { Tabs } from "../../../design-system";
import Reception from "./Reception";
import OpenDesignStudio from "./OpenDesignStudio";
import CompanyHeadquarters from "./CompanyHeadquarters";
import Meeting from "./Meeting";
import Presentation from "./Presentation";
import "./ODWorkspace.css";

const TABS = [
  { key: "headquarters", label: "Headquarters" },
  { key: "studio", label: "Studio" },
  { key: "meeting", label: "Meeting" },
  { key: "presentation", label: "Presentation" },
];

/**
 * MWO-OD-001 — the navigable Open Design prototype. No backend, no
 * Runtime integration, no AI execution, mock data only.
 *
 * Two phases: an onboarding sequence (Reception -> Open Design, before a
 * Business Blueprint exists) and, once sealed, the tabbed Company
 * Headquarters app (Headquarters / Studio / Meeting / Presentation),
 * mirroring the same Tabs-based navigation LTSAWorkspace already uses.
 */
export default function ODWorkspace() {
  const [phase, setPhase] = useState("reception");
  const [blueprint, setBlueprint] = useState(null);
  const [hasSeenBriefing, setHasSeenBriefing] = useState(false);
  const [activeKey, setActiveKey] = useState("headquarters");

  function handleBlueprintSealed(sealedBlueprint) {
    setBlueprint(sealedBlueprint);
    setPhase("tabbed");
    setActiveKey("headquarters");
  }

  if (phase === "reception") {
    return <Reception onEnter={() => setPhase("open-design")} />;
  }

  if (phase === "open-design") {
    return <OpenDesignStudio onComplete={handleBlueprintSealed} />;
  }

  const PAGES = {
    headquarters: (
      <CompanyHeadquarters
        blueprint={blueprint}
        hasSeenBriefing={hasSeenBriefing}
        onDismissBriefing={() => setHasSeenBriefing(true)}
        onNavigate={setActiveKey}
      />
    ),
    studio: <OpenDesignStudio onComplete={handleBlueprintSealed} />,
    meeting: <Meeting />,
    presentation: <Presentation blueprint={blueprint} />,
  };

  return (
    <div className="od-workspace">
      <div className="od-workspace-nav">
        <Tabs items={TABS} activeKey={activeKey} onChange={setActiveKey} />
      </div>

      <div className="od-workspace-content">{PAGES[activeKey]}</div>
    </div>
  );
}
