import { useEffect, useReducer, useRef, useState } from "react";
import type { ApplicationDraft } from "../shared/demo";
import { programs, schedules } from "../shared/demo";
import {
  applicationReducer,
  applicationScenarios,
  initialApplication,
  type ApplicationScenario,
} from "../shared/application";
import { Button, Field, Notice, SelectField } from "../shared/ui";

const unavailableCopy = {
  expired: [
    "Enlace vencido · Escenario local",
    "En un flujo conectado deberá solicitar un nuevo enlace al asesor. Aquí puede volver al escenario disponible para seguir probando.",
  ],
  used: [
    "Enlace ya utilizado · Escenario local",
    "No complete otro formulario desde este enlace. En el flujo futuro un asesor deberá comprobar el estado de la solicitud; esta demo no consulta registros.",
  ],
  invalid: [
    "Enlace no válido · Escenario local",
    "Revise el enlace con su asesor. Esta vista ilustra un acceso bloqueado, sin validar identidad ni tokens reales.",
  ],
};

export function ApplicationForm() {
  const [state, dispatch] = useReducer(applicationReducer, undefined, () =>
    initialApplication(),
  );
  const [pendingReset, setPendingReset] = useState<ApplicationScenario | null>(
    null,
  );
  const [focusVersion, setFocusVersion] = useState(0);
  const statusRef = useRef<HTMLHeadingElement>(null);
  const handledFocusVersion = useRef(0);
  const { draft, errors, scenario, step } = state;

  useEffect(() => {
    if (focusVersion === handledFocusVersion.current) return;
    handledFocusVersion.current = focusVersion;
    const firstError = Object.keys(errors)[0];
    if (firstError)
      document.getElementById(`application-${firstError}`)?.focus();
    else statusRef.current?.focus();
  }, [focusVersion, errors]);

  function move(type: "validate" | "confirm" | "edit") {
    dispatch({ type });
    setFocusVersion((value) => value + 1);
  }
  function change(nextDraft: ApplicationDraft) {
    dispatch({ type: "change", draft: nextDraft });
  }
  function requestReset(nextScenario: ApplicationScenario) {
    if (
      draft.name ||
      draft.email ||
      draft.program ||
      draft.schedule ||
      draft.consent ||
      step !== "capture"
    ) {
      setPendingReset(nextScenario);
    } else {
      dispatch({ type: "reset", scenario: nextScenario });
      setFocusVersion((value) => value + 1);
    }
  }
  const summary = (
    <dl className="detail-list">
      <dt>Nombre ficticio</dt>
      <dd>{draft.name}</dd>
      <dt>Correo de ejemplo</dt>
      <dd>{draft.email}</dd>
      <dt>Programa de ejemplo</dt>
      <dd>{draft.program}</dd>
      <dt>Jornada de ejemplo</dt>
      <dd>{draft.schedule}</dd>
      <dt>Datos de prueba</dt>
      <dd>Uso exclusivo de datos ficticios confirmado</dd>
    </dl>
  );

  return (
    <section className="panel application-panel">
      <div className="panel-heading">
        <div>
          <h2>Su interés, paso a paso</h2>
          <p>
            Complete, revise y confirme únicamente datos ficticios. Ningún paso
            registra una solicitud real.
          </p>
        </div>
      </div>
      <details className="mb-6">
        <summary>Probar estados de enlace · Solo demostración</summary>
        <p className="scope-text">
          Cambiar el escenario descarta el formulario con su confirmación. No
          hay token, vencimiento real ni control de acceso.
        </p>
        <SelectField
          id="application-scenario"
          label="Escenario de enlace ficticio"
          value={scenario}
          options={[...applicationScenarios]}
          onChange={(event) =>
            requestReset(event.target.value as ApplicationScenario)
          }
        />
      </details>
      {pendingReset !== null && (
        <section
          className="reset-confirmation"
          aria-label="Confirmar descarte del formulario"
        >
          <p>
            Se descartarán los datos, la revisión y la confirmación de este
            formulario local.
          </p>
          <div className="actions">
            <Button
              onClick={() => {
                dispatch({ type: "reset", scenario: pendingReset });
                setPendingReset(null);
                setFocusVersion((value) => value + 1);
              }}
            >
              Descartar formulario local
            </Button>
            <Button variant="secondary" onClick={() => setPendingReset(null)}>
              Conservar formulario
            </Button>
          </div>
        </section>
      )}
      {scenario !== "valid" ? (
        <div>
          <h3 ref={statusRef} tabIndex={-1}>
            {unavailableCopy[scenario][0]}
          </h3>
          <Notice>{unavailableCopy[scenario][1]}</Notice>
          <Button className="mt-4" onClick={() => requestReset("valid")}>
            Volver al escenario disponible
          </Button>
        </div>
      ) : (
        <>
          <ol
            className="flex flex-wrap gap-4 mb-6 scope-text"
            aria-label="Pasos del formulario"
          >
            {(["capture", "review", "confirmed"] as const).map(
              (value, index) => (
                <li
                  key={value}
                  aria-current={value === step ? "step" : undefined}
                >
                  {index + 1}.{" "}
                  {value === "capture"
                    ? "Completar"
                    : value === "review"
                      ? "Revisar"
                      : "Confirmar"}
                  {value === step ? " · Paso actual" : ""}
                </li>
              ),
            )}
          </ol>
          {step === "confirmed" ? (
            <div className="confirmation">
              <h3 ref={statusRef} tabIndex={-1}>
                Formulario validado en la demostración
              </h3>
              <Notice>
                No se registró ninguna solicitud, persona o matrícula. No se
                envió información a SIIE ni a una API.
              </Notice>
              {summary}
              <p className="scope-text">
                La revisión académica humana será una fase separada. Esta
                confirmación desaparece al salir, recargar o restablecer la
                demo.
              </p>
              <Button onClick={() => requestReset("valid")}>
                Probar otro formulario
              </Button>
            </div>
          ) : step === "review" ? (
            <div>
              <h3 ref={statusRef} tabIndex={-1}>
                Revise antes de confirmar
              </h3>
              <Notice>
                Los datos solo se validaron en esta pestaña. Confirme por
                separado o vuelva a corregirlos.
              </Notice>
              {summary}
              <div className="actions">
                <Button
                  disabled={pendingReset !== null}
                  onClick={() => move("confirm")}
                >
                  Confirmar formulario local
                </Button>
                <Button
                  variant="secondary"
                  disabled={pendingReset !== null}
                  onClick={() => move("edit")}
                >
                  Editar datos
                </Button>
              </div>
            </div>
          ) : (
            <form
              noValidate
              onSubmit={(event) => {
                event.preventDefault();
                if (pendingReset === null) move("validate");
              }}
            >
              <h3 ref={statusRef} tabIndex={-1}>
                Datos de la demostración
              </h3>
              <p className="scope-text">
                Todos los campos son obligatorios en este ejemplo. Catálogo y
                campos provisionales; aviso legal y datos definitivos pendientes
                de aprobación.
              </p>
              {!!Object.keys(errors).length && (
                <Notice error>
                  Revise los campos señalados. El formulario no se confirmó.
                </Notice>
              )}
              <Field
                id="application-name"
                label="Nombre ficticio"
                required
                autoComplete="off"
                value={draft.name}
                maxLength={100}
                error={errors.name}
                onChange={(event) =>
                  change({ ...draft, name: event.target.value })
                }
              />
              <Field
                id="application-email"
                label="Correo de ejemplo"
                type="email"
                required
                autoComplete="off"
                placeholder="demo@example.invalid"
                maxLength={160}
                hint="No ingrese correos o datos personales reales."
                error={errors.email}
                value={draft.email}
                onChange={(event) =>
                  change({ ...draft, email: event.target.value })
                }
              />
              <SelectField
                id="application-program"
                label="Programa de interés"
                required
                options={[
                  { value: "", label: "Seleccione un programa de ejemplo" },
                  ...programs,
                ]}
                value={draft.program}
                error={errors.program}
                onChange={(event) =>
                  change({ ...draft, program: event.target.value })
                }
              />
              <SelectField
                id="application-schedule"
                label="Jornada"
                required
                options={[
                  { value: "", label: "Seleccione una jornada de ejemplo" },
                  ...schedules,
                ]}
                value={draft.schedule}
                error={errors.schedule}
                onChange={(event) =>
                  change({ ...draft, schedule: event.target.value })
                }
              />
              <div className="field">
                <label className="checkbox-label" htmlFor="application-consent">
                  <input
                    id="application-consent"
                    type="checkbox"
                    required
                    checked={draft.consent}
                    aria-invalid={!!errors.consent}
                    aria-describedby={
                      errors.consent
                        ? "application-consent-error"
                        : "application-consent-hint"
                    }
                    onChange={(event) =>
                      change({ ...draft, consent: event.target.checked })
                    }
                  />
                  Confirmo que utilizaré únicamente datos ficticios para probar
                  este diseño.
                </label>
                <small id="application-consent-hint">
                  Esto no es consentimiento legal ni autorización de tratamiento
                  de datos reales.
                </small>
                {errors.consent && (
                  <small id="application-consent-error" className="field-error">
                    {errors.consent}
                  </small>
                )}
              </div>
              <div className="actions">
                <Button type="submit" disabled={pendingReset !== null}>
                  Validar formulario local
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => requestReset("valid")}
                >
                  Limpiar
                </Button>
              </div>
            </form>
          )}
        </>
      )}
      <p className="scope-text mt-6">
        Estado temporal de esta vista; sin guardar, enviar ni inscribir. Token
        de uso único, validación en servidor, privacidad y registro real
        pertenecen al corte conectado, después de fase 1.
      </p>
    </section>
  );
}
