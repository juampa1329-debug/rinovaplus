import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { Button, Notice } from "../shared/ui";
import { useInstitution } from "./api";
import "./provider-account.css";

type Snapshot = {
  provider: string;
  checked_at: string;
  currency?: string;
  account_status?: string;
  key_status?: string;
  account?: {
    total_credits: number;
    total_usage: number;
    remaining: number;
  } | null;
  key?: {
    usage: number;
    usage_daily: number | null;
    usage_weekly: number | null;
    usage_monthly: number | null;
    limit: number | null;
    limit_remaining: number | null;
    limit_reset: string | null;
  } | null;
  quota?: {
    used: number;
    limit: number;
    remaining: number;
    tier: string;
    reset_at: number | null;
  };
  voice_slots?: { voice_slots_used: number | null; voice_limit: number | null };
  overage_enabled?: boolean | null;
};
const names: Record<string, string> = {
  openrouter: "OpenRouter",
  elevenlabs: "ElevenLabs",
};
const links: Record<string, { billing: string; usage: string }> = {
  openrouter: {
    billing: "https://openrouter.ai/settings/credits",
    usage: "https://openrouter.ai/activity",
  },
  elevenlabs: {
    billing: "https://elevenlabs.io/app/subscription",
    usage: "https://elevenlabs.io/app/usage",
  },
};
const units = (n: number | null | undefined) =>
  n == null
    ? "No informado"
    : n.toLocaleString("es-CO", { maximumFractionDigits: 6 });
const dollars = (n: number | null | undefined) =>
  n == null ? "No informado" : `USD ${units(n)}`;
const localDate = (value: string | number) =>
  new Date(value).toLocaleString("es-CO", { timeZone: "America/Bogota" });

export function ProviderAccount({ provider }: { provider: string }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  if (!names[provider]) return null;
  return (
    <section className="panel" aria-label={`Cuenta de ${names[provider]}`}>
      <h3>Saldo y consumo · {names[provider]}</h3>
      <p>
        Consulta los datos de la cuenta del proveedor y el momento de la última
        lectura.
      </p>
      <Button
        type="button"
        variant="secondary"
        onClick={(event) => {
          trigger.current = event.currentTarget;
          setOpen(true);
        }}
      >
        Saldo y consumo de {names[provider]}
      </Button>
      {open && (
        <AccountDialog
          provider={provider}
          close={() => {
            setOpen(false);
            trigger.current?.focus();
          }}
        />
      )}
    </section>
  );
}

function AccountDialog({
  provider,
  close,
}: {
  provider: string;
  close: () => void;
}) {
  const { call } = useInstitution();
  const dialog = useRef<HTMLDialogElement>(null);
  const active = useRef(true);
  const [value, setValue] = useState<Snapshot | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      const next = await call<Snapshot>(`provider-balance/${provider}`);
      if (active.current) setValue(next);
    } catch (e) {
      if (active.current)
        setError(
          e instanceof Error
            ? e.message
            : "No se pudo consultar la cuenta. Revisa la clave y vuelve a consultar.",
        );
    } finally {
      if (active.current) setBusy(false);
    }
  }, [call, provider]);
  useLayoutEffect(() => {
    dialog.current?.showModal?.();
    dialog.current?.querySelector("button")?.focus();
  }, []);
  useEffect(() => {
    active.current = true;
    void call<Snapshot>(`provider-balance/${provider}`)
      .then((next) => {
        if (active.current) setValue(next);
      })
      .catch((e: unknown) => {
        if (active.current)
          setError(
            e instanceof Error
              ? e.message
              : "No se pudo consultar la cuenta. Revisa la clave y vuelve a consultar.",
          );
      })
      .finally(() => {
        if (active.current) setBusy(false);
      });
    return () => {
      active.current = false;
    };
  }, [call, provider]);
  const dismiss = () => {
    dialog.current?.close?.();
    close();
  };
  return (
    <dialog
      ref={dialog}
      className="provider-account-dialog operation-error-dialog"
      aria-labelledby="provider-account-title"
      onCancel={(e) => {
        e.preventDefault();
        dismiss();
      }}
    >
      <div className="provider-account-content">
        <div className="provider-account-heading">
          <h2 id="provider-account-title">
            Saldo y consumo · {names[provider]}
          </h2>
          <Button type="button" variant="quiet" onClick={dismiss}>
            Cerrar detalle
          </Button>
        </div>
        <p>
          Datos de toda la cuenta o clave, incluidos otros proyectos. Los
          límites internos de RinovaPlus se administran por separado.
        </p>
        {busy && (
          <div role="status" className="provider-account-loading">
            Consultando al proveedor…
          </div>
        )}
        {error && (
          <Notice error>
            {error}
            {value && " Se conserva la consulta anterior, con su fecha."}
          </Notice>
        )}
        {value && (
          <>
            {provider === "openrouter" ? (
              <div className="provider-account-grid">
                <section className="panel">
                  <h3>Saldo global de la cuenta</h3>
                  {value.account ? (
                    <>
                      <strong className="provider-account-amount">
                        {dollars(value.account.remaining)}
                      </strong>
                      <dl>
                        <dt>Créditos adquiridos</dt>
                        <dd>{dollars(value.account.total_credits)}</dd>
                        <dt>Consumo acumulado</dt>
                        <dd>{dollars(value.account.total_usage)}</dd>
                      </dl>
                    </>
                  ) : (
                    <Notice>
                      {value.account_status === "management_key_required"
                        ? "OpenRouter exige una Management API key para consultar el saldo global. Puedes guardarla en Credenciales → Clave de administración de OpenRouter. La clave de modelos se conserva."
                        : value.account_status === "management_key_rejected"
                          ? "OpenRouter rechazó la clave de administración. Comprueba que sea una Management API key vigente; la clave para modelos es distinta."
                          : "El saldo global no está disponible en esta consulta. Vuelve a consultar o abre la cuenta de OpenRouter."}
                    </Notice>
                  )}
                </section>
                <section className="panel">
                  <h3>Consumo de la clave de modelos</h3>
                  {value.key ? (
                    <>
                      <dl>
                        <dt>Acumulado</dt>
                        <dd>{dollars(value.key.usage)}</dd>
                        <dt>Hoy</dt>
                        <dd>{dollars(value.key.usage_daily)}</dd>
                        <dt>Semana</dt>
                        <dd>{dollars(value.key.usage_weekly)}</dd>
                        <dt>Mes</dt>
                        <dd>{dollars(value.key.usage_monthly)}</dd>
                        <dt>Límite de la clave</dt>
                        <dd>
                          {value.key.limit == null
                            ? "Sin límite fijado"
                            : dollars(value.key.limit)}
                        </dd>
                        <dt>Disponible dentro del límite</dt>
                        <dd>
                          {value.key.limit == null
                            ? "Depende del saldo de la cuenta"
                            : dollars(value.key.limit_remaining)}
                        </dd>
                      </dl>
                      <p>
                        El cupo de la clave no representa el saldo global. Los
                        períodos de consumo los informa OpenRouter.
                      </p>
                    </>
                  ) : (
                    <Notice error>
                      {value.key_status === "key_rejected"
                        ? "OpenRouter rechazó la clave de modelos. Revisa la credencial guardada."
                        : "No se pudo consultar el consumo de esta clave."}
                    </Notice>
                  )}
                </section>
              </div>
            ) : (
              value.quota && (
                <div className="provider-account-grid">
                  <section className="panel">
                    <h3>Unidades disponibles del plan</h3>
                    <strong className="provider-account-amount">
                      {units(value.quota.remaining)}
                    </strong>
                    <p>Plan: {value.quota.tier || "No informado"}</p>
                    <dl>
                      <dt>Utilizadas</dt>
                      <dd>{units(value.quota.used)}</dd>
                      <dt>Cupo del período</dt>
                      <dd>{units(value.quota.limit)}</dd>
                      <dt>Renovación informada · Bogotá</dt>
                      <dd>
                        {value.quota.reset_at
                          ? localDate(value.quota.reset_at * 1000)
                          : "No informada"}
                      </dd>
                    </dl>
                    {value.quota.limit > 0 && (
                      <progress
                        aria-label="Uso del plan ElevenLabs"
                        max={value.quota.limit}
                        value={Math.min(value.quota.used, value.quota.limit)}
                      />
                    )}
                    <p>
                      Son unidades del plan, no dinero disponible ni una
                      cantidad garantizada de minutos. El consumo depende del
                      modelo y del servicio.
                    </p>
                  </section>
                  <section className="panel">
                    <h3>Capacidad de voces</h3>
                    <dl>
                      <dt>Voces utilizadas</dt>
                      <dd>{units(value.voice_slots?.voice_slots_used)}</dd>
                      <dt>Cupo de voces</dt>
                      <dd>{units(value.voice_slots?.voice_limit)}</dd>
                      <dt>Plan admite sobreconsumo</dt>
                      <dd>
                        {value.overage_enabled == null
                          ? "No informado"
                          : value.overage_enabled
                            ? "Sí; revisa sus condiciones en ElevenLabs"
                            : "No"}
                      </dd>
                    </dl>
                    <p>
                      Esta consulta conserva el plan y sus límites. Puedes
                      gestionar el plan en la cuenta oficial de ElevenLabs.
                    </p>
                  </section>
                </div>
              )
            )}
            <p className="provider-account-checked">
              Consultado: {localDate(value.checked_at)} · Bogotá
              {error ? " · Consulta anterior" : ""}
            </p>
          </>
        )}
        <div className="institution-actions">
          <Button
            type="button"
            disabled={busy}
            variant="secondary"
            onClick={() => {
              setBusy(true);
              setError("");
              void load();
            }}
          >
            Actualizar saldo y consumo
          </Button>
          <a
            href={links[provider].billing}
            target="_blank"
            rel="noopener noreferrer"
          >
            {provider === "openrouter"
              ? "Recargar en OpenRouter ↗"
              : "Gestionar plan en ElevenLabs ↗"}
          </a>
          <a
            href={links[provider].usage}
            target="_blank"
            rel="noopener noreferrer"
          >
            Ver uso en {names[provider]} ↗
          </a>
        </div>
        <p>
          Los enlaces abren la plataforma oficial. Tú revisas y confirmas
          cualquier pago o cambio de plan allí.
        </p>
      </div>
    </dialog>
  );
}
