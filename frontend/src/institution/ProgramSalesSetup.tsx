import { useState } from "react";
import { api, mutation, type Catalog } from "../modules/agents/api";
import { Button, Field, Notice, SelectField } from "../shared/ui";
import "./sales.css";
import { OperationDialog } from "./ErrorFeedback";

type Plan = {
  guide_name: string;
  guide_id: string;
  digest: string;
  provider: string;
  model: string;
  guide_changes: string[];
  items: {
    program_id: number;
    name: string;
    school: string;
    schedule: string;
    action: string;
    missing: string[];
    price_pending: boolean;
    system_prompt: string;
  }[];
};
type AdLinks = {
  revision: number;
  items: { ad_id: string; program_id: number }[];
};

export function ProgramSalesSetup({
  catalog,
  disabled,
  onSaved,
}: {
  catalog: Catalog;
  disabled: boolean;
  onSaved: () => Promise<unknown>;
}) {
  const [guide, setGuide] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [school, setSchool] = useState("");
  const [ad, setAd] = useState("");
  const [program, setProgram] = useState("");
  const [links, setLinks] = useState<AdLinks | null>(null);
  async function act(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setFeedback("");
    try {
      await work();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "No se pudo completar la configuración.",
      );
    } finally {
      setBusy(false);
    }
  }
  const blocked = disabled || busy;
  return (
    <details className="panel sales-setup">
      <summary>Especialistas por programa y origen de anuncios</summary>
      <p>
        Prepara un agente con su propio system prompt por cada programa y
        jornada. Usa el modelo y los límites del orientador existente; no
        modifica anuncios, gasto, matrícula ni datos de SIIE.
      </p>
      {error && (
        <Notice error>
          {error} Revisa la selección y vuelve a preparar la vista previa si
          cambió el catálogo.
        </Notice>
      )}
      {feedback && <Notice>{feedback}</Notice>}
      {error && (
        <OperationDialog
          guidance={{
            title: "No se pudo completar la configuración comercial",
            detail: error,
            nextStep:
              "Revisa el orientador, el programa y tus permisos. Si cambió el catálogo o la configuración, prepara nuevamente la vista previa. Tu selección se conserva.",
          }}
          dismiss={() => setError("")}
        />
      )}
      <SelectField
        id="sales-guide"
        label="Orientador de Admisiones"
        value={guide}
        disabled={blocked}
        options={[
          { value: "", label: "Selecciona el orientador activo" },
          ...catalog.agents
            .filter((v) => v.level === "guide" && v.state === "active")
            .map((v) => ({ value: v.id, label: v.name })),
        ]}
        onChange={(event) => {
          setGuide(event.target.value);
          setPlan(null);
          setConfirmed(false);
        }}
      />
      <Button
        type="button"
        disabled={blocked || !guide}
        onClick={() =>
          void act(async () => {
            setPlan(
              await api<Plan>(
                "/sales/preview?guide_id=" + encodeURIComponent(guide),
              ),
            );
            setConfirmed(false);
          })
        }
      >
        Preparar especialistas de todos los programas
      </Button>
      {plan && (
        <section aria-label="Revisión de especialistas">
          <h3>
            {plan.items.length} programas · {plan.provider} / {plan.model}
          </h3>
          <p>
            El orientador incorporará: {plan.guide_changes.join(", ")}. Cada
            especialista conserva su ficha como fuente viva; los datos ausentes
            se comunican como pendientes.
          </p>
          <SelectField
            id="sales-plan-school"
            label="Filtrar especialistas por escuela"
            value={school}
            options={[
              { value: "", label: "Todas las escuelas" },
              ...Array.from(new Set(plan.items.map((v) => v.school)))
                .sort()
                .map((v) => ({ value: v, label: v || "Sin escuela" })),
            ]}
            onChange={(event) => setSchool(event.target.value)}
          />
          <div className="sales-program-review">
            {plan.items
              .filter((v) => !school || v.school === school)
              .map((item) => (
                <article key={item.program_id}>
                  <div>
                    <strong>{item.name}</strong>
                    <small>
                      {item.school} · {item.schedule}
                    </small>
                  </div>
                  <span>
                    {item.action === "create"
                      ? "Crear especialista"
                      : "Conservar agente existente"}
                  </span>
                  <p>
                    {item.price_pending ? "Precio por confirmar. " : ""}
                    {item.missing.length
                      ? `Pendientes de ficha: ${item.missing.join(", ")}.`
                      : "Contenido académico disponible."}
                  </p>
                  <details>
                    <summary>Ver system prompt del especialista</summary>
                    <p>{item.system_prompt}</p>
                  </details>
                </article>
              ))}
          </div>
          <label className="sales-switch">
            <input
              type="checkbox"
              checked={confirmed}
              disabled={blocked}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            Revisé la creación de especialistas, las 20 skills y la
            actualización comercial automática del orientador
          </label>
          <Button
            type="button"
            disabled={blocked || !confirmed}
            onClick={() =>
              void act(async () => {
                const result = await api<{
                  created: number;
                  preserved: number;
                }>("/sales/provision", "POST", {
                  operation_id: crypto.randomUUID(),
                  guide_id: plan.guide_id,
                  preview_digest: plan.digest,
                  confirmed: true,
                });
                setFeedback(
                  `${result.created} especialistas creados; ${result.preserved} existentes conservados. Puedes ajustar el prompt y la voz en cada agente.`,
                );
                setPlan(null);
                setConfirmed(false);
                await onSaved();
              })
            }
          >
            Crear especialistas revisados
          </Button>
        </section>
      )}
      <details className="sales-ad-links">
        <summary>Vincular anuncios de WhatsApp con programas</summary>
        <p>
          Asocia el ID del anuncio de Meta con la ficha y jornada correcta.
          Cuando WhatsApp entregue su referencia, el orientador usará ese
          programa sin volver a preguntarlo. El texto del anuncio no autoriza
          precios ni condiciones.
        </p>
        <Button
          type="button"
          variant="quiet"
          disabled={blocked}
          onClick={() =>
            void act(async () =>
              setLinks(await api<AdLinks>("/sales/ad-links")),
            )
          }
        >
          Consultar vinculaciones
        </Button>
        {links && (
          <>
            <Field
              id="sales-ad-id"
              label="ID del anuncio en Meta"
              value={ad}
              maxLength={40}
              onChange={(event) =>
                setAd(event.target.value.replace(/[^0-9]/g, ""))
              }
            />
            <SelectField
              id="sales-ad-program"
              label="Programa y jornada del anuncio"
              value={program}
              options={[
                { value: "", label: "Selecciona el programa" },
                ...catalog.programs.items.map((v) => ({
                  value: String(v.program_id),
                  label: v.name + " · " + (v.schedule ?? ""),
                })),
              ]}
              onChange={(event) => setProgram(event.target.value)}
            />
            <Button
              type="button"
              disabled={blocked || !ad || !program}
              onClick={() =>
                void act(async () => {
                  const items = [
                    ...links.items.filter((v) => v.ad_id !== ad),
                    { ad_id: ad, program_id: Number(program) },
                  ];
                  await api("/sales/ad-links", "PUT", {
                    ...mutation(links.revision),
                    items,
                  });
                  setLinks(await api<AdLinks>("/sales/ad-links"));
                  setFeedback(
                    "Anuncio vinculado localmente. No se modificó Meta ni el gasto.",
                  );
                  setAd("");
                  setProgram("");
                })
              }
            >
              Guardar vínculo del anuncio
            </Button>
            <ul>
              {links.items.map((item) => (
                <li key={item.ad_id}>
                  Anuncio {item.ad_id} →{" "}
                  {catalog.programs.items.find(
                    (v) => v.program_id === item.program_id,
                  )?.name ?? "Programa no disponible"}
                </li>
              ))}
            </ul>
          </>
        )}
      </details>
    </details>
  );
}
