import { useState } from "react";
import { Badge, Button, Field, Notice } from "../shared/ui";
import { useResource } from "./Settings";

export function NoContactList() {
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const data = useResource<{
    items: { id: string; name: string; phone: string; stage: string }[];
    has_more: boolean;
  }>(`workspace/contact-preferences?q=${encodeURIComponent(query)}&offset=${offset}`);
  return <section className="panel" aria-label="Lista No contactar">
    <h2>No contactar</h2>
    <p>Solicitudes de baja guardadas en el historial. Estas personas quedan excluidas de campañas y seguimientos. El cierre por silencio y la falta de autorización se consultan por separado.</p>
    <Field id="no-contact-search" label="Buscar en No contactar" value={query}
      onChange={e => { setQuery(e.target.value); setOffset(0); }} />
    <Button variant="quiet" onClick={() => void data.reload()}>Actualizar lista</Button>
    {data.error && <Notice error>No se pudo consultar la lista de bajas.</Notice>}
    {!data.value && !data.error && <p>Consultando solicitudes…</p>}
    {data.value && <>
      {data.value.items.length === 0 && <p>No hay solicitudes de baja para esta búsqueda.</p>}
      <div className="campaign-table"><table><caption>Preferencias vigentes de los contactos</caption>
        <thead><tr><th>Persona</th><th>Teléfono</th><th>Etapa comercial</th><th>Preferencia</th></tr></thead>
        <tbody>{data.value.items.map(v => <tr key={v.id}><td>{v.name}</td><td>{v.phone}</td><td>{v.stage}</td><td><Badge>No contactar</Badge></td></tr>)}</tbody>
      </table></div>
      <div className="institution-actions">
        <Button variant="quiet" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 25))}>Anterior</Button>
        <span>Página {offset / 25 + 1}</span>
        <Button variant="quiet" disabled={!data.value.has_more} onClick={() => setOffset(offset + 25)}>Siguiente</Button>
      </div>
    </>}
  </section>;
}
