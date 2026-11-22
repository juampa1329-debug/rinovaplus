import { Button, Field, SelectField } from "../shared/ui";

type Contact = {
  label: string;
  number: string;
  use: "whatsapp" | "calls" | "both";
  active: boolean;
  note: string;
};
export function InstitutionContacts({
  value,
  onChange,
}: {
  value: unknown;
  onChange: (value: Contact[]) => void;
}) {
  const items = (value ?? []) as Contact[];
  const update = (index: number, patch: Partial<Contact>) =>
    onChange(
      items.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
  return (
    <section className="panel" aria-label="Contactos públicos de CBN">
      <h3>¿Cómo pueden contactar a CBN?</h3>
      <p>
        La IA usa este directorio en todos los canales. El número de WhatsApp
        conectado no se ofrece para llamadas a menos que lo indiques aquí.
      </p>
      {!items.length && (
        <p>
          Aún no hay contactos públicos. Añade uno y guarda los cambios de
          Institución.
        </p>
      )}
      {items.map((item, index) => (
        <fieldset key={index}>
          <legend>Contacto {index + 1}</legend>
          <div className="form-grid">
            <Field
              id={`public-contact-label-${index}`}
              label="Nombre del contacto"
              value={item.label}
              maxLength={80}
              onChange={(e) => update(index, { label: e.target.value })}
            />
            <Field
              id={`public-contact-number-${index}`}
              label="Número con indicativo"
              type="tel"
              value={item.number}
              maxLength={24}
              onChange={(e) => update(index, { number: e.target.value })}
            />
            <SelectField
              id={`public-contact-use-${index}`}
              label="Uso autorizado"
              value={item.use}
              options={[
                { value: "whatsapp", label: "Sólo WhatsApp" },
                { value: "calls", label: "Sólo llamadas" },
                { value: "both", label: "WhatsApp y llamadas" },
              ]}
              onChange={(e) =>
                update(index, { use: e.target.value as Contact["use"] })
              }
            />
            <Field
              id={`public-contact-note-${index}`}
              label="Indicaciones públicas (opcional)"
              value={item.note}
              maxLength={200}
              onChange={(e) => update(index, { note: e.target.value })}
            />
          </div>
          <label>
            <input
              type="checkbox"
              checked={item.active}
              onChange={(e) => update(index, { active: e.target.checked })}
            />{" "}
            Ofrecer este contacto
          </label>
          <Button
            variant="quiet"
            onClick={() => onChange(items.filter((_, i) => i !== index))}
          >
            Quitar contacto {index + 1}
          </Button>
        </fieldset>
      ))}
      <Button
        variant="secondary"
        disabled={items.length >= 12}
        onClick={() =>
          onChange([
            ...items,
            { label: "", number: "", use: "calls", active: true, note: "" },
          ])
        }
      >
        Añadir contacto público
      </Button>
      <p>
        Estos cambios se aplican al pulsar Guardar cambios. No conectan un canal
        ni habilitan llamadas desde el CRM.
      </p>
    </section>
  );
}
