import { useState } from "react";
import { Badge, Button, Notice, SelectField } from "../shared/ui";
import { useInstitution, useTask } from "./api";

type Result = {
  operation_id: string;
  state: string;
  case: string;
  text?: string;
  code?: string;
  real_backup: boolean;
  provider_calls: number;
  checks?: Record<string, boolean>;
  usage?: { promptTokenCount?: number; candidatesTokenCount?: number };
  free_quota?: { used: number; limit: number; remaining: number };
  reserved_usd_micros?: number;
  cost_cap_usd_micros?: number;
  trace: {
    fallback_used?: boolean;
    latency_ms?: number;
    attempts?: {
      provider: string;
      model: string;
      state: string;
      role: string;
      code?: string;
    }[];
  };
};

export function LanguageRehearsal({
  revision,
  enabled,
  dirty,
}: {
  revision: number;
  enabled: boolean;
  dirty: boolean;
}) {
  const { call } = useInstitution();
  const task = useTask();
  const [scenario, setScenario] = useState("unavailable");
  const [audience, setAudience] = useState("message");
  const [allowPaid, setAllowPaid] = useState(false);
  const [operation, setOperation] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const reset = () => {
    setOperation(null);
    setResult(null);
  };
  const labels: Record<string, string> = {
    program_preserved: "Programa conservado",
    duration_preserved: "Duración conservada",
    schedule_preserved: "Jornada conservada",
    name_preserved_or_private_excluded:
      audience === "message" ? "Nombre recordado" : "Memoria privada excluida",
  };
  return (
    <section className="panel" aria-label="Ensayo de conmutación P21">
      <h3>Simular una caída · P21</h3>
      <p>
        El principal se simula dentro del ensayo; Gemini y los chats reales
        siguen funcionando. Ante un rechazo 503 o 429 se consulta el respaldo
        guardado con información ficticia. Los modelos de pago requieren tu
        autorización y el ensayo reserva como máximo USD 0,05 en total, además
        de respetar los presupuestos diarios. No se envían mensajes, no se
        modifica la ficha CRM ni la configuración.
      </p>
      <fieldset disabled={task.busy}>
        <SelectField
          id="language-rehearsal-case"
          label="Situación a simular"
          value={scenario}
          disabled={
            !!operation &&
            (!result || ["running", "uncertain"].includes(result.state))
          }
          options={[
            { value: "unavailable", label: "Principal no disponible · 503" },
            { value: "rate_limited", label: "Principal saturado · 429" },
            {
              value: "healthy",
              label: "Principal saludable · sin consulta externa",
            },
            { value: "human", label: "Control Humano · no debe consultar IA" },
          ]}
          onChange={(event) => {
            setScenario(event.target.value);
            reset();
          }}
        />
        <SelectField
          id="language-rehearsal-audience"
          label="Contexto del ensayo"
          value={audience}
          disabled={
            !!operation &&
            (!result || ["running", "uncertain"].includes(result.state))
          }
          options={[
            {
              value: "message",
              label: "Mensaje privado ficticio · continuidad",
            },
            {
              value: "comment",
              label: "Comentario público ficticio · sin datos privados",
            },
          ]}
          onChange={(event) => {
            setAudience(event.target.value);
            reset();
          }}
        />
        {dirty && (
          <Notice>
            Guarda o descarta los cambios antes de probar la política publicada.
          </Notice>
        )}
        <label>
          <input
            type="checkbox"
            checked={allowPaid}
            disabled={!!operation}
            onChange={(event) => setAllowPaid(event.target.checked)}
          />
          Autorizar respaldo de pago · máximo USD 0,05 por ensayo
        </label>
        {!enabled && (
          <Notice>
            Habilita y guarda un respaldo antes de realizar el ensayo.
          </Notice>
        )}
        <Button
          disabled={dirty || !enabled || !!result}
          onClick={() =>
            void task.run(async () => {
              const id = operation ?? crypto.randomUUID();
              setOperation(id);
              setResult(
                await call<Result>("language-rehearsals", "POST", {
                  operation_id: id,
                  revision,
                  case: scenario,
                  audience,
                  allow_paid: allowPaid,
                }),
              );
            }, "Ensayo registrado. Revisa el resultado y los intentos.")
          }
        >
          Ejecutar simulación controlada
        </Button>
        {operation && (
          <Button
            variant="secondary"
            onClick={() =>
              void task.run(async () => {
                setResult(
                  await call<Result>(`language-rehearsals/${operation}`),
                );
              }, "Resultado recuperado sin repetir la generación.")
            }
          >
            Consultar resultado sin repetir
          </Button>
        )}
        {result && (
          <Button
            variant="quiet"
            disabled={["running", "uncertain"].includes(result.state)}
            onClick={reset}
          >
            Preparar otra simulación
          </Button>
        )}
      </fieldset>
      {task.notices}
      {result && (
        <section aria-label="Resultado del ensayo P21" aria-live="polite">
          <Badge>
            {result.state === "passed"
              ? "Ensayo superado"
              : result.state === "running"
                ? "En curso · consulta el resultado"
                : "Requiere revisión"}
          </Badge>
          <p>
            {result.real_backup
              ? "Respaldo real consultado"
              : "Sin consulta externa"}{" "}
            · {result.provider_calls} intentos de generación al proveedor.
          </p>
          <p>
            Principal simulado. Mensajes enviados: 0. Escrituras en la ficha
            CRM: 0. Configuración publicada conservada.
          </p>
          {!!result.trace.attempts?.length && (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Ruta</th>
                    <th>Proveedor y modelo</th>
                    <th>Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trace.attempts.map((attempt, index) => (
                    <tr key={index}>
                      <td>
                        {attempt.role === "primary"
                          ? "Principal · simulado"
                          : "Respaldo · real"}
                      </td>
                      <td>
                        {attempt.provider} · {attempt.model}
                      </td>
                      <td>
                        {attempt.state === "completed" ? "Respondió" : "Falló"}
                        {attempt.code ? ` · ${attempt.code}` : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {result.text && <blockquote>{result.text}</blockquote>}
          {result.checks && (
            <ul>
              {Object.entries(result.checks).map(([name, passed]) => (
                <li key={name}>
                  {passed ? "✓" : "Revisar"} · {labels[name] ?? name}
                </li>
              ))}
            </ul>
          )}
          {result.usage?.promptTokenCount !== undefined && (
            <p>
              Tokens reportados: {result.usage.promptTokenCount} entrada /{" "}
              {result.usage.candidatesTokenCount ?? "sin reporte"} salida.
            </p>
          )}
          {result.reserved_usd_micros !== undefined && (
            <p>
              Reserva máxima calculada: USD{" "}
              {(result.reserved_usd_micros / 1000000).toFixed(6)} · tope del
              ensayo: USD{" "}
              {((result.cost_cap_usd_micros ?? 50000) / 1000000).toFixed(2)}. Es
              una reserva conservadora, no la factura del proveedor.
            </p>
          )}
          {result.code && (
            <p>
              Diagnóstico: {result.code}. Consulta el resultado antes de repetir
              una solicitud incierta.
            </p>
          )}
          {result.free_quota && (
            <p>
              Cupo gratuito diario reportado por OpenRouter:{" "}
              {result.free_quota.used} usados / {result.free_quota.limit} ·{" "}
              {result.free_quota.remaining} disponibles. Este contador no
              informa del límite por minuto ni garantiza capacidad del modelo.
            </p>
          )}
          {result.code === "openrouter_free_daily_limit" && (
            <Notice error>
              El proveedor reporta que se agotó el cupo gratuito diario. Espera
              su renovación o revisa el plan de la cuenta. RinovaPlus conserva
              la política; sólo consulta las alternativas de pago guardadas
              cuando están autorizadas para este ensayo.
            </Notice>
          )}
          {result.code === "provider_rate_limited" && (
            <Notice error>
              El respaldo también limitó la solicitud. Si queda cupo diario,
              puede ser saturación temporal o un límite por minuto del modelo.
              Revisa los modelos y límites antes de preparar otro ensayo.
            </Notice>
          )}
          <small>Operación: {result.operation_id}</small>
          <details>
            <summary>Traza técnica del ensayo</summary>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </section>
      )}
    </section>
  );
}
