import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { InstitutionApp } from "./InstitutionApp";
import "../shared/tailwind.css";
import "../shared/tokens.css";
import "../shared/styles.css";
import "../shared/pilot.css";
import "./institution.css";
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <InstitutionApp />
  </StrictMode>,
);
