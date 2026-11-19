import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { InstitutionApp } from "./InstitutionApp";
import { WorkspaceP3 } from "./Workspace";
import { VersionNotice } from "./VersionNotice";
import "../shared/tailwind.css";
import "../shared/tokens.css";
import "../shared/styles.css";
import "../shared/pilot.css";
import "./institution.css";
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <VersionNotice />
    <InstitutionApp core={WorkspaceP3} />
  </StrictMode>,
);
