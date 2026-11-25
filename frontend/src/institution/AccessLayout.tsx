import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { BrandMark } from "../shared/BrandMark";
import { Icon } from "../shared/Icon";
import { useTheme } from "../shared/theme";
import "./login.css";

function ConnectionMap() {
  const svg = useRef<SVGSVGElement>(null);
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const compactLayout = window.matchMedia("(max-width: 900px)");
    const syncPlayback = () => {
      if (paused || reducedMotion.matches || compactLayout.matches || document.hidden) {
        svg.current?.pauseAnimations?.();
      } else {
        svg.current?.unpauseAnimations?.();
      }
    };
    syncPlayback();
    reducedMotion.addEventListener("change", syncPlayback);
    compactLayout.addEventListener("change", syncPlayback);
    document.addEventListener("visibilitychange", syncPlayback);
    return () => {
      reducedMotion.removeEventListener("change", syncPlayback);
      compactLayout.removeEventListener("change", syncPlayback);
      document.removeEventListener("visibilitychange", syncPlayback);
    };
  }, [paused]);
  return (
    <div className="access-flow" data-flow-paused={paused}>
    <div className="access-connections" aria-hidden="true">
      <svg ref={svg} className="access-connections-lines" viewBox="0 0 600 350" fill="none">
        <circle className="access-orbit" cx="270" cy="190" r="128" />
        <circle className="access-orbit access-orbit-dotted" cx="270" cy="190" r="150" />
        <path d="M127 163C162 163 166 190 196 190M270 47C270 78 280 86 270 116M344 180C380 175 375 142 416 142M326 238C356 246 359 292 415 292" />
        <circle className="access-signal" cx="362" cy="101" r="4" />
        {[
          { name: "channels", path: "M127 163C162 163 166 190 196 190", start: 0.06, end: 0.22 },
          { name: "memory", path: "M270 47C270 78 280 86 270 116", start: 0.26, end: 0.42 },
          { name: "knowledge", path: "M416 142C375 142 380 175 344 180", start: 0.46, end: 0.62 },
          { name: "team", path: "M326 238C356 246 359 292 415 292", start: 0.68, end: 0.84 },
        ].map(({ name, path, start, end }) => (
          <circle key={name} className="access-flow-signal" r="3.5" opacity="0">
            <animateMotion path={path} dur="8s" repeatCount="indefinite" calcMode="linear" keyPoints="0;0;1;1" keyTimes={`0;${start};${end};1`} />
            <animate attributeName="opacity" dur="8s" repeatCount="indefinite" values="0;0;1;1;0;0" keyTimes={`0;${start};${start + 0.02};${end - 0.02};${end};1`} />
          </circle>
        ))}
      </svg>
      <div className="access-agent">
        <div className="access-agent-mark"><BrandMark width={78} /><span>+</span></div>
        <span>Tu agente de IA</span>
      </div>
      <div className="access-node access-node-channels"><Icon name="inbox" />Canales</div>
      <div className="access-node access-node-memory">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="m2 7 10-5 10 5-10 5L2 7Zm0 5 10 5 10-5M2 17l10 5 10-5" /></svg>
        Memoria
      </div>
      <div className="access-node access-node-knowledge"><Icon name="knowledge" />Conocimiento</div>
      <div className="access-node access-node-team"><Icon name="user" />Tu equipo</div>
    </div>
    <button className="access-flow-control" type="button" aria-pressed={paused} onClick={() => setPaused(!paused)}>
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
        {paused ? <path d="m7 4 9 6-9 6V4Z" /> : <path d="M7 4v12M13 4v12" />}
      </svg>
      {paused ? "Reanudar animación" : "Pausar animación"}
    </button>
    </div>
  );
}

export function AccessLayout({ children }: { children: ReactNode }) {
  const theme = useTheme();
  return (
    <main className="institution-login" data-access-theme={theme.theme}>
      <header className="access-header">
        <div className="access-wordmark">
          <span className="access-brand-mark" aria-hidden="true" />
          <span>Rinova<span className="access-wordmark-plus">Plus</span></span>
        </div>
        <div className="access-appearance" role="group" aria-label="Apariencia">
          {([
            ["light", "sun", "Claro"],
            ["dark", "moon", "Oscuro"],
            ["system", "monitor", "Sistema"],
          ] as const).map(([value, icon, label]) => (
            <button type="button" key={value} aria-pressed={theme.preference === value} onClick={() => theme.chooseTheme(value)}>
              <Icon name={icon} /><span>{label}</span>
            </button>
          ))}
        </div>
      </header>
      <div className="access-main">
        <div className="access-intro">
          <p className="access-eyebrow">Tu CRM, impulsado por agentes de IA</p>
          <p className="access-tagline">La innovación<br />que conecta.</p>
          <p className="access-description">Agentes, memoria y equipo.<br />Todo conectado para acompañar mejor.</p>
          <ConnectionMap />
        </div>
        <section className="access-form" aria-labelledby="access-title">
          <p className="access-card-label">Acceso institucional</p>
          {children}
        </section>
      </div>
      <footer className="access-copyright">
        <span>Desarrollado por la Corporación Bolivariana del Norte</span>
        <span>© 2026 RinovaPlus</span>
      </footer>
    </main>
  );
}
