import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { GeneralPreview } from "./GeneralPreview";
import "../shared/tailwind.css";
import "../shared/tokens.css";
import "../shared/styles.css";
import "../shared/pilot.css";
import "./general.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <GeneralPreview />
  </StrictMode>,
);
