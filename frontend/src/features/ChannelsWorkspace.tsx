import { useEffect, useState } from "react";
import { useRuntime } from "../shared/runtimeCapabilities";
import { useRoute } from "../shared/navigation";
import { useTheme, type ThemePreference } from "../shared/theme";
import {
  Badge,
  Button,
  EmptyState,
  PageHeading,
  SelectField,
} from "../shared/ui";
import { Icon } from "../shared/Icon";
import { ChannelsUiPanel } from "./ChannelsUiPanel";
import "./channels-ui.css";

export function ChannelsWorkspace() {
  const { capabilities } = useRuntime();
  const { preference, chooseTheme } = useTheme();
  const route = useRoute();
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    document.title = "Canales · CRM CBN";
  }, []);
  if (capabilities.profile !== "channels") return null;
  const available = route === "settings" || !window.location.hash;
  return (
    <div className="app-shell pilot-shell channels-ui">
      <a
        href="#channels-main"
        className="skip-link"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("channels-main")?.focus();
        }}
      >
        Saltar al contenido
      </a>
      <aside className="sidebar">
        <button
          type="button"
          className="sidebar-logo-toggle"
          aria-label="Menú CRM CBN"
          aria-expanded={menuOpen}
          aria-controls="channels-navigation"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          <Icon name="menu" />
          <span>CRM CBN</span>
        </button>
        <nav
          id="channels-navigation"
          aria-label="Navegación principal"
          className={menuOpen ? "mobile-open" : ""}
        >
          <a
            className="nav-link"
            href="#/settings"
            aria-current={available ? "page" : undefined}
            onClick={() => setMenuOpen(false)}
          >
            <Icon name="settings" />
            <span>Canales</span>
          </a>
        </nav>
        <div className="sidebar-footer">
          <strong>Institución educativa</strong>
          <small>Copia de ensayo</small>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>Ajustes de la institución</span>
          <SelectField
            id="channels-theme"
            label="Apariencia"
            value={preference}
            onChange={(e) => chooseTheme(e.target.value as ThemePreference)}
            options={[
              { value: "system", label: "Sistema" },
              { value: "light", label: "Claro" },
              { value: "dark", label: "Oscuro" },
            ]}
          />
        </header>
        <main id="channels-main" tabIndex={-1}>
          <PageHeading
            title="Canales"
            description="Configuración y actividad local de los canales de la institución."
          >
            <Badge>Copia de ensayo</Badge>
          </PageHeading>
          {available ? (
            <ChannelsUiPanel capabilities={capabilities.channels} />
          ) : (
            <section className="panel">
              <EmptyState title="Sección no habilitada">
                Esta copia permite trabajar con la configuración de Canales.
              </EmptyState>
              <Button
                onClick={() => {
                  window.location.hash = "/settings";
                }}
              >
                Volver a Canales
              </Button>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
