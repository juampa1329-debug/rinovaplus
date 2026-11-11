import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { RuntimeProvider } from "./shared/runtimeCapabilities";
import "./shared/tailwind.css";
import "./shared/tokens.css";
import "./shared/styles.css";
import "./shared/pilot.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RuntimeProvider>
      <App />
    </RuntimeProvider>
  </StrictMode>,
);
