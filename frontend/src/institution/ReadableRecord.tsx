import type { ReactNode } from "react";
import "./readable-record.css";

const labels: Record<string, string> = {
  body: "Mensaje",
  text: "Texto",
  header: "Encabezado",
  footer: "Pie del mensaje",
  name: "Nombre",
  phone: "Teléfono",
  email: "Correo",
  origen: "Archivo de origen",
  hoja: "Hoja",
  fila: "Fila",
  datos_exportados: "Información del formulario",
  fecha_excel: "Fecha registrada en origen",
  sha256: "Huella del archivo",
  source_files: "Archivos de origen",
  programs: "Programas de interés",
};
function valueView(value: unknown, depth = 0): ReactNode {
  if (value === null || value === undefined || value === "") return "Sin dato";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (typeof value !== "object") return String(value);
  if (depth >= 4) return <span>Información adicional anidada</span>;
  if (Array.isArray(value))
    return (
      <ul>
        {value.slice(0, 100).map((v, i) => (
          <li key={i}>{valueView(v, depth + 1)}</li>
        ))}
      </ul>
    );
  return (
    <dl className="readable-record-fields">
      {Object.entries(value)
        .filter(
          ([key]) =>
            !["sha256", "sistema_fecha_excel", "fecha_excel"].includes(key),
        )
        .slice(0, 100)
        .map(([key, v]) => (
          <div key={key}>
            <dt>{labels[key] || key.replaceAll("_", " ")}</dt>
            <dd>{valueView(v, depth + 1)}</dd>
          </div>
        ))}
    </dl>
  );
}

export function ReadableRecord({ text }: { text: string }) {
  const start = text.indexOf("{");
  let record: unknown;
  if (start >= 0 && text.length <= 200_000) {
    try {
      record = JSON.parse(text.slice(start));
    } catch {
      /* Ordinary prose stays intact. */
    }
  }
  if (!record || typeof record !== "object" || Array.isArray(record))
    return (
      <div className="readable-record-text">
        {text || "Sin texto registrado."}
      </div>
    );
  const source = record as Record<string, unknown>;
  const imported =
    typeof source.origen === "string" &&
    source.datos_exportados &&
    typeof source.datos_exportados === "object";
  return (
    <div className="readable-record">
      {text.slice(0, start).trim() && <p>{text.slice(0, start).trim()}</p>}
      {imported ? (
        <>
          {valueView(source.datos_exportados)}
          <details>
            <summary>Origen de la preinscripción</summary>
            {valueView({
              origen: source.origen,
              hoja: source.hoja,
              fila: source.fila,
            })}
          </details>
        </>
      ) : (
        valueView(source)
      )}
    </div>
  );
}
