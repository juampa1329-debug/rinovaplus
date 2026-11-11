import { useCallback, useEffect, useState } from "react";
import {
  Badge,
  Button,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../../../shared/ui";
import {
  aiRequest,
  type AiSnapshot,
  type AiModel,
} from "../../../shared/aiSettings";
import { AudioReply } from "../pages/AssistantChat";

type Policy = {
  primary_model: string;
  fallback_model: string;
  temperature: number;
  system_prompt: string;
  max_tokens: number;
};
type Snapshot = {
  revision: number;
  enabled: boolean;
  settings: Policy;
  openrouter_configured: boolean;
  global_ai_enabled: boolean;
  outbound_enabled: boolean;
};
type Source = {
  id: string;
  document_id?: string;
  title: string;
  page: number | null;
  text: string;
  matched_terms?: number;
  source_kind?: string;
};
type Document = {
  id: string;
  title: string;
  filename: string;
  state: string;
  revision: number;
  bytes: number;
  chunks: number;
};
type Conversation = {
  id: string;
  name: string;
  control: string;
  memory_revision: number;
  generation: number;
};
type Memory = {
  revision: number;
  generation: number;
  baseline_sequence: number;
  facts: Record<
    string,
    {
      value: string;
      quote: string;
      source_message_id: string;
      authority: string;
    }
  >;
};
type AcademicProgram = {
  program_id: number;
  offering_id: number;
  name: string;
  code: string;
  semesters: number;
  modality: string;
  schedule: string;
};
type AcademicCatalog = {
  items: AcademicProgram[];
  period: { id: number; label: string };
  total: number;
  has_more: boolean;
  offset: number;
};
type Institutional = {
  period: { id: number; label: string };
  selected_program: AcademicProgram | null;
  semester: number;
  catalog_total: number;
  fingerprint: string;
  selection_required: boolean;
};
type Context = {
  messages: { role: string; content: string }[];
  sources: Source[];
  institutional: Institutional;
  network_called: boolean;
};
type Preview = {
  text: string;
  provider: string;
  model: string;
  audio_id?: string;
  voice_status: string;
  voice_error?: string;
  voice_provider: string;
  admissions_sources: {
    id: string;
    title: string;
    page: number | null;
    source_kind: string;
  }[];
  institutional: Institutional;
  knowledge_missing: boolean;
  documents_missing: boolean;
};
const root = "/api/v1/ai";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(root + path, {
    ...options,
    cache: "no-store",
    headers: {
      "X-CRM-Local": "1",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  let value;
  try {
    value = await response.json();
  } catch {
    throw new Error(
      response.ok
        ? "La respuesta no es válida. No se confirmó la operación."
        : `No se completó la operación (HTTP ${response.status}). No se confirmó ningún resultado.`,
    );
  }
  if (!response.ok) {
    const messages: Record<string, string> = {
      admissions_activation_requires_openrouter_and_global_gates:
        "Para activar, configure OpenRouter en APIs, seleccione el modelo y habilite IA y conexiones externas.",
      admissions_revision_conflict:
        "La configuración cambió. Actualice antes de guardar.",
      memory_revision_conflict:
        "La memoria cambió. Vuelva a consultarla antes de reiniciar.",
      knowledge_revision_conflict: "El documento cambió. Actualice la lista.",
      knowledge_pdf_no_text_ocr_required:
        "El PDF no contiene texto extraíble. Cargue una versión con texto; OCR no está habilitado.",
      knowledge_pdf_limit_or_invalid:
        "No se pudo extraer el PDF dentro de los límites. Use PDF con texto de hasta 150 páginas o TXT UTF-8.",
      knowledge_pdf_or_txt_required: "Seleccione PDF o TXT UTF-8.",
      admissions_schema_required:
        "La configuración de admisiones aún no está disponible.",
      knowledge_size_limit: "El documento supera el límite de 5 MB.",
      provider_temporary_failure:
        "El proveedor informó un fallo temporal. No se generó respuesta.",
      provider_response_timeout:
        "El proveedor no respondió dentro del tiempo de lectura. No se generó texto ni voz; no se reintentó automáticamente.",
      provider_invalid_json:
        "La respuesta del proveedor no contenía JSON válido. No se generó texto ni voz.",
      provider_protocol_failure:
        "La comunicación con el proveedor terminó con un error de protocolo o codificación. No se confirmó una respuesta.",
      provider_model_unavailable:
        "El modelo seleccionado no está disponible en el endpoint consultado con esta credencial (HTTP 404). Seleccione otro modelo confirmado.",
      model_catalog_required:
        "Cargue los modelos actuales y seleccione uno de la lista antes de probar.",
      institutional_active_period_ambiguous:
        "No se puede determinar la oferta vigente; consulte al administrador.",
      institutional_program_not_in_active_offer:
        "El programa seleccionado no está en la oferta del período activo. Actualice el catálogo.",
    };
    const diagnostic =
      path.endsWith("/preview") &&
      ["catalog", "generation"].includes(value.phase)
        ? ` ${value.provider ?? "Proveedor"} · ${value.phase === "catalog" ? "catálogo" : "generación"}${Number.isInteger(value.upstream_status) ? ` · HTTP ${value.upstream_status}` : ""}.`
        : "";
    throw new Error(
      (messages[value.code ?? value.detail] ??
        `No se completó la operación (${value.code ?? value.detail ?? response.status}).`) +
        diagnostic,
    );
  }
  return value as T;
}

export function AdmissionsSettingsPanel() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [draft, setDraft] = useState<Policy | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [models, setModels] = useState<AiModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsLoaded, setModelsLoaded] = useState(false);
  const [modelsError, setModelsError] = useState("");
  const loadModels = useCallback(async () => {
    setModelsLoading(true);
    setModelsError("");
    try {
      const value = await aiRequest<{ models: AiModel[] }>(
        "models/openrouter",
        "POST",
        {},
      );
      setModels(value.models);
      setModelsLoaded(true);
    } catch (failure) {
      setModelsError((failure as Error).message);
    } finally {
      setModelsLoading(false);
    }
  }, []);
  async function load() {
    try {
      const value = await request<Snapshot>("/settings");
      setSnapshot(value);
      setDraft(value.settings);
      setEnabled(value.enabled);
      setError("");
      if (value.openrouter_configured && value.outbound_enabled)
        void loadModels();
    } catch (failure) {
      setError((failure as Error).message);
    }
  }
  useEffect(() => {
    let live = true;
    void request<Snapshot>("/settings")
      .then((value) => {
        if (!live) return;
        setSnapshot(value);
        setDraft(value.settings);
        setEnabled(value.enabled);
        setError("");
        if (value.openrouter_configured && value.outbound_enabled)
          void loadModels();
      })
      .catch((failure: Error) => live && setError(failure.message));
    return () => {
      live = false;
    };
  }, [loadModels]);
  async function save() {
    if (!snapshot || !draft) return;
    setBusy(true);
    setError("");
    setFeedback("");
    try {
      const value = await request<Snapshot>("/settings", {
        method: "PUT",
        body: JSON.stringify({
          revision: snapshot.revision,
          enabled,
          settings: draft,
        }),
      });
      setSnapshot(value);
      setDraft(value.settings);
      setEnabled(value.enabled);
      setFeedback("Política de admisiones actualizada correctamente.");
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function modelOptions(current: string, placeholder: string) {
    const options = models.map((model) => ({
      value: model.id,
      label: model.name === model.id ? model.id : `${model.name} · ${model.id}`,
    }));
    if (current && !models.some((model) => model.id === current))
      options.unshift({
        value: current,
        label: `${current} · selección actual${modelsLoaded ? "; no figura en el catálogo consultado" : "; catálogo pendiente"}`,
      });
    return [{ value: "", label: placeholder }, ...options];
  }
  return (
    <section
      className="admissions-ai-section"
      aria-labelledby="admissions-ai-title"
    >
      <div className="panel-heading">
        <h3 id="admissions-ai-title">Asistente de admisiones · OpenRouter</h3>
        <Badge>
          {snapshot?.enabled ? "Automático activo" : "Automático desactivado"}
        </Badge>
      </div>
      <p>
        Política del Inbox con memoria y fuentes publicadas. La clave se
        administra cifrada en Ajustes → APIs → OpenRouter.
      </p>
      {error && <Notice error>{error}</Notice>}
      {feedback && <Notice>{feedback}</Notice>}
      {draft && snapshot && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
          className="admissions-ai-form"
        >
          <p>
            OpenRouter:{" "}
            {snapshot.openrouter_configured
              ? "credencial configurada"
              : "sin credencial"}{" "}
            · IA global: {snapshot.global_ai_enabled ? "activa" : "desactivada"}{" "}
            · Conexiones externas:{" "}
            {snapshot.outbound_enabled ? "habilitadas" : "deshabilitadas"}.
          </p>
          <div className="form-actions">
            <Button
              variant="secondary"
              disabled={modelsLoading || busy}
              onClick={() => void loadModels()}
            >
              {modelsLoading
                ? "Cargando modelos de OpenRouter…"
                : modelsLoaded
                  ? "Actualizar modelos de OpenRouter"
                  : "Cargar modelos de OpenRouter"}
            </Button>
          </div>
          <p role="status" aria-live="polite">
            {modelsLoading
              ? "Consultando el catálogo de OpenRouter. Sus cambios se conservan."
              : modelsLoaded
                ? models.length
                  ? `${models.length} ${models.length === 1 ? "modelo de texto recibido" : "modelos de texto recibidos"} de OpenRouter. El catálogo no confirma permisos de inferencia.`
                  : "OpenRouter no devolvió modelos de texto compatibles. Puede volver a consultar el catálogo; la selección actual se conserva."
                : "El catálogo todavía no se consultó. Configure la credencial y autorice las consultas externas en Ajustes → APIs → OpenRouter."}
          </p>
          {modelsError && (
            <Notice error>
              {modelsError} Puede volver a cargar el catálogo; sus cambios se
              conservan.
            </Notice>
          )}
          <SelectField
            id="admissions-primary"
            label="Modelo principal de OpenRouter"
            value={draft.primary_model}
            disabled={modelsLoading}
            options={modelOptions(
              draft.primary_model,
              "Seleccione un modelo de OpenRouter",
            )}
            onChange={(event) =>
              setDraft({ ...draft, primary_model: event.target.value })
            }
          />
          <SelectField
            id="admissions-fallback"
            label="Modelo de respaldo de OpenRouter"
            value={draft.fallback_model}
            disabled={modelsLoading}
            options={modelOptions(
              draft.fallback_model,
              "Sin modelo de respaldo",
            )}
            onChange={(event) =>
              setDraft({ ...draft, fallback_model: event.target.value })
            }
          />
          <p className="muted">
            Consultar modelos no guarda ni activa la política. No modifica el
            modelo del Asistente.
          </p>
          <Field
            id="admissions-temperature"
            label="Temperatura"
            type="number"
            min={0}
            max={2}
            step={0.1}
            value={draft.temperature}
            onChange={(event) =>
              setDraft({ ...draft, temperature: Number(event.target.value) })
            }
          />
          <Field
            id="admissions-tokens"
            label="Máximo de tokens de respuesta"
            type="number"
            min={128}
            max={2000}
            value={draft.max_tokens}
            onChange={(event) =>
              setDraft({ ...draft, max_tokens: Number(event.target.value) })
            }
          />
          <TextArea
            id="admissions-system"
            label="Instrucción institucional de admisiones"
            rows={5}
            maxLength={6000}
            value={draft.system_prompt}
            onChange={(event) =>
              setDraft({ ...draft, system_prompt: event.target.value })
            }
          />
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(event) => setEnabled(event.target.checked)}
            />
            Responder automáticamente a mensajes externos nuevos con control IA
          </label>
          <p className="muted">
            Activar comienza desde mensajes futuros. El control humano
            prevalece. Sin fuentes suficientes, se transfiere a un asesor y se
            crea una tarea de prioridad alta.
          </p>
          <div className="form-actions">
            <Button type="submit" disabled={busy}>
              {busy ? "Guardando…" : "Guardar política de admisiones"}
            </Button>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => void load()}
            >
              Actualizar política
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}

export function KnowledgePanel() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [offset, setOffset] = useState(0);
  const [more, setMore] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadId, setUploadId] = useState("");
  const [title, setTitle] = useState("");
  const [official, setOfficial] = useState<Record<string, boolean>>({});
  const [query, setQuery] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [review, setReview] = useState<
    { id: string; page: number; text: string }[]
  >([]);
  const [reviewDocument, setReviewDocument] = useState<Document | null>(null);
  const [reviewOffset, setReviewOffset] = useState(0);
  const [reviewMore, setReviewMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  async function load() {
    try {
      const value = await request<{ items: Document[]; has_more: boolean }>(
        `/knowledge?offset=${offset}`,
      );
      setDocuments(value.items);
      setMore(value.has_more);
      setError("");
    } catch (failure) {
      setError((failure as Error).message);
    }
  }
  useEffect(() => {
    void load();
  }, [offset]);
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    setFeedback("");
    try {
      await action();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function upload() {
    if (!file || !title.trim()) return;
    if (file.size > 5000000)
      throw new Error("El documento supera el límite de 5 MB.");
    await request(
      `/knowledge/${uploadId}/content?filename=${encodeURIComponent(file.name)}&title=${encodeURIComponent(title.trim())}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/octet-stream" },
        body: file,
      },
    );
    setFile(null);
    setUploadId("");
    setTitle("");
    setFeedback(
      "Documento guardado como borrador. Revise la fuente y publíquela explícitamente para incluirla en las respuestas.",
    );
    await load();
  }
  async function change(document: Document, state: string) {
    await request(`/knowledge/${document.id}`, {
      method: "PUT",
      body: JSON.stringify({
        revision: document.revision,
        state,
        official: !!official[document.id],
      }),
    });
    setOfficial({ ...official, [document.id]: false });
    setFeedback("Estado del documento actualizado.");
    setSources([]);
    await load();
    if (state === "deleted") {
      setReview([]);
      setReviewDocument(null);
    }
  }
  async function reviewChunks(document: Document, pageOffset = 0) {
    const value = await request<{
      items: { id: string; page: number; text: string }[];
      has_more: boolean;
    }>(`/knowledge/${document.id}/chunks?offset=${pageOffset}`);
    setReview(value.items);
    setReviewDocument(document);
    setReviewOffset(pageOffset);
    setReviewMore(value.has_more);
  }
  return (
    <section
      className="panel admissions-ai-section"
      aria-labelledby="knowledge-title"
    >
      <div className="panel-heading">
        <h2 id="knowledge-title">Conocimiento institucional</h2>
        <Badge>Fuentes institucionales</Badge>
      </div>
      <p>
        Consulte la oferta vigente, tarifas, asignaturas y tipos documentales.
        Los documentos oficiales complementan esta información.
      </p>
      {error && <Notice error>{error}</Notice>}
      {feedback && <Notice>{feedback}</Notice>}
      <form
        className="admissions-ai-form"
        onSubmit={(event) => {
          event.preventDefault();
          void run(upload);
        }}
      >
        <Field
          id="knowledge-title-input"
          label="Título de la fuente"
          maxLength={160}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <Field
          id="knowledge-file"
          label="Documento PDF o TXT UTF-8 · máximo 5 MB"
          type="file"
          accept=".pdf,.txt"
          key={file ? uploadId : "empty"}
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setUploadId(crypto.randomUUID());
          }}
        />
        {file && (
          <p>
            {file.name} · {file.size.toLocaleString("es-CO")} bytes
          </p>
        )}
        <div className="form-actions">
          <Button type="submit" disabled={busy || !file || !title.trim()}>
            {busy ? "Procesando…" : "Cargar como borrador"}
          </Button>
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => void load()}
          >
            Actualizar documentos
          </Button>
        </div>
      </form>
      <p className="muted">
        PDF con texto hasta 150 páginas, hasta 300.000 caracteres y 250
        fragmentos. No se ejecuta OCR ni búsqueda semántica por embeddings.
      </p>
      <div className="admissions-document-list">
        {documents.length === 0 && (
          <p>
            No hay documentos cargados. No se inventará contexto institucional.
          </p>
        )}
        {documents.map((document) => (
          <article key={document.id} className="admissions-document">
            <h3>{document.title}</h3>
            <p>
              {document.filename} · {document.chunks} fragmentos ·{" "}
              {document.state === "published"
                ? "Publicado"
                : document.state === "draft"
                  ? "Borrador"
                  : "Deshabilitado"}
            </p>
            {document.state !== "published" && (
              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={!!official[document.id]}
                  onChange={(event) =>
                    setOfficial({
                      ...official,
                      [document.id]: event.target.checked,
                    })
                  }
                />
                Confirmo que esta fuente está revisada y es oficial
              </label>
            )}
            <div className="form-actions">
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => void run(() => reviewChunks(document))}
              >
                Revisar fragmentos
              </Button>
              {document.state !== "published" && (
                <Button
                  disabled={busy || !official[document.id]}
                  onClick={() => void run(() => change(document, "published"))}
                >
                  Publicar fuente
                </Button>
              )}
              {document.state === "published" && (
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void run(() => change(document, "disabled"))}
                >
                  Retirar de respuestas
                </Button>
              )}
              <Button
                variant="quiet"
                disabled={busy}
                onClick={() => void run(() => change(document, "deleted"))}
              >
                Eliminar documento
              </Button>
            </div>
          </article>
        ))}
      </div>
      {reviewDocument && (
        <details open>
          <summary>Revisión: {reviewDocument.title}</summary>
          {review.map((chunk) => (
            <article className="admissions-document" key={chunk.id}>
              <h3>Página {chunk.page}</h3>
              <p>{chunk.text}</p>
            </article>
          ))}
          <div className="form-actions">
            <Button
              variant="secondary"
              disabled={busy || reviewOffset === 0}
              onClick={() =>
                void run(() =>
                  reviewChunks(reviewDocument, Math.max(0, reviewOffset - 10)),
                )
              }
            >
              Fragmentos anteriores
            </Button>
            <Button
              variant="secondary"
              disabled={busy || !reviewMore}
              onClick={() =>
                void run(() => reviewChunks(reviewDocument, reviewOffset + 10))
              }
            >
              Fragmentos siguientes
            </Button>
            <Button
              variant="quiet"
              onClick={() => {
                setReview([]);
                setReviewDocument(null);
              }}
            >
              Cerrar revisión
            </Button>
          </div>
        </details>
      )}
      <div className="form-actions">
        <Button
          variant="secondary"
          disabled={busy || offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 25))}
        >
          Anteriores
        </Button>
        <Button
          variant="secondary"
          disabled={busy || !more}
          onClick={() => setOffset(offset + 25)}
        >
          Siguientes
        </Button>
      </div>
      <form
        className="admissions-ai-form"
        onSubmit={(event) => {
          event.preventDefault();
          void run(async () => {
            const result = await request<{ sources: Source[] }>(
              `/knowledge/search?q=${encodeURIComponent(query)}`,
            );
            setSources(result.sources);
            setFeedback(
              result.sources.length
                ? "Contexto encontrado en fuentes publicadas."
                : "No hay coincidencias en las fuentes publicadas. Corresponde derivar al asesor.",
            );
          });
        }}
      >
        <Field
          id="knowledge-query"
          label="Consultar contexto publicado"
          value={query}
          maxLength={2000}
          onChange={(event) => setQuery(event.target.value)}
        />
        <Button type="submit" disabled={busy || !query.trim()}>
          Buscar contexto sin llamar a IA
        </Button>
      </form>
      {sources.map((source) => (
        <article className="admissions-document" key={source.id}>
          <h3>
            {source.title} · página {source.page}
          </h3>
          <p>{source.text}</p>
          <small>
            Fragmento {source.id} · {source.matched_terms} términos coincidentes
          </small>
        </article>
      ))}
    </section>
  );
}

export function MemoryPanel() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [offset, setOffset] = useState(0);
  const [more, setMore] = useState(false);
  const [selected, setSelected] = useState("");
  const [memory, setMemory] = useState<Memory | null>(null);
  const [question, setQuestion] = useState("");
  const [context, setContext] = useState<Context | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewConversation, setPreviewConversation] = useState("");
  const [previewModel, setPreviewModel] = useState("");
  const [previewModels, setPreviewModels] = useState<AiModel[]>([]);
  const [previewProvider, setPreviewProvider] = useState("");
  const [academic, setAcademic] = useState<AcademicCatalog | null>(null);
  const [programId, setProgramId] = useState("");
  const [semester, setSemester] = useState("1");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function load() {
    const result = await request<{ items: Conversation[]; has_more: boolean }>(
      `/conversations?offset=${offset}`,
    );
    setConversations(result.items);
    setMore(result.has_more);
    setAcademic(await request<AcademicCatalog>("/institutional/programs"));
  }
  useEffect(() => {
    void run(load);
  }, [offset]);
  useEffect(() => {
    setMemory(null);
    setContext(null);
    setPreview(null);
    setPreviewConversation("");
    setFeedback("");
    if (selected)
      void run(async () =>
        setMemory(await request<Memory>(`/conversations/${selected}/memory`)),
      );
  }, [selected]);
  async function generatePreview() {
    setPreview(null);
    const current = await aiRequest<AiSnapshot>("settings");
    let conversation = previewConversation;
    const selection = {
      program_id: programId ? Number(programId) : null,
      semester: Number(semester) || 1,
    };
    if (!conversation) {
      const created = await request<{ conversation_id: string }>(
        `/conversations/${selected}/preview-session`,
        {
          method: "POST",
          body: JSON.stringify({
            preview_model: previewModel,
            question,
            ...selection,
          }),
        },
      );
      conversation = created.conversation_id;
      setPreviewConversation(conversation);
    }
    const value = await request<Preview>(`/conversations/${selected}/preview`, {
      method: "POST",
      body: JSON.stringify({
        revision: current.revision,
        credential_revision: current.credential_revision,
        conversation_id: conversation,
        turn_id: crypto.randomUUID().replaceAll("-", ""),
        prompt: question,
        history: [],
        search: "",
        preview_model: previewModel,
        ...selection,
      }),
    });
    setPreview(value);
  }
  async function loadPreviewModels() {
    const current = await aiRequest<AiSnapshot>("settings");
    const result = await aiRequest<{ models: AiModel[] }>(
      `models/${current.settings.provider}`,
      "POST",
      {},
    );
    setPreviewModels(result.models);
    setPreviewProvider(current.settings.provider);
    setPreviewModel("");
    setPreviewConversation("");
    setFeedback("Catálogo actualizado.");
  }
  const names: Record<string, string> = {
    program_interest: "Programa de interés declarado",
    schedule_availability: "Disponibilidad de horario declarada",
    registration_reported:
      "Inscripción declarada, sin verificación institucional",
  };
  return (
    <section
      className="panel admissions-ai-section"
      aria-labelledby="memory-title"
    >
      <div className="panel-heading">
        <h2 id="memory-title">Memoria del aspirante</h2>
        <Badge>Declaraciones con evidencia</Badge>
      </div>
      <p>
        La memoria pertenece a la conversación existente. No confirma matrícula
        ni pagos y no une personas por teléfono.
      </p>
      {academic && (
        <Notice>
          Período activo {academic.period.label} · {academic.total} programas
          ofrecidos.
        </Notice>
      )}
      {error && <Notice error>{error}</Notice>}
      {feedback && <Notice>{feedback}</Notice>}
      <div className="field">
        <label htmlFor="admissions-memory-conversation">Conversación</label>
        <select
          id="admissions-memory-conversation"
          value={selected}
          disabled={busy}
          onChange={(event) => setSelected(event.target.value)}
        >
          <option value="">Seleccione una conversación</option>
          {conversations.map((conversation) => (
            <option key={conversation.id} value={conversation.id}>
              {conversation.name} ·{" "}
              {conversation.control === "human"
                ? "control humano"
                : "control IA"}
            </option>
          ))}
        </select>
      </div>
      <div className="form-actions">
        <Button
          variant="secondary"
          disabled={busy || offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 25))}
        >
          Anteriores
        </Button>
        <Button
          variant="secondary"
          disabled={busy || !more}
          onClick={() => setOffset(offset + 25)}
        >
          Siguientes
        </Button>
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() => void run(load)}
        >
          Actualizar conversaciones
        </Button>
      </div>
      {memory && (
        <>
          <p>
            Revisión {memory.revision} · generación {memory.generation}
          </p>
          {Object.keys(memory.facts).length === 0 && (
            <p>No hay datos recordados para esta conversación.</p>
          )}
          <dl>
            {Object.entries(memory.facts).map(([field, fact]) => (
              <div className="admissions-document" key={field}>
                <dt>{names[field] ?? field}</dt>
                <dd>{fact.value}</dd>
                <dd>Declaración: “{fact.quote}”</dd>
                <dd>Mensaje de origen: {fact.source_message_id}</dd>
              </div>
            ))}
          </dl>
          <div className="form-actions">
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() =>
                void run(async () =>
                  setMemory(
                    await request<Memory>(`/conversations/${selected}/memory`),
                  ),
                )
              }
            >
              Consultar memoria
            </Button>
            <Button
              variant="quiet"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  const result = await request<Memory>(
                    `/conversations/${selected}/context-reset`,
                    {
                      method: "POST",
                      body: JSON.stringify({ revision: memory.revision }),
                    },
                  );
                  setMemory(result);
                  setContext(null);
                  setFeedback(
                    "Memoria reiniciada. El chat se conserva y el contexto anterior queda excluido de futuras respuestas.",
                  );
                })
              }
            >
              Reiniciar memoria de esta conversación
            </Button>
          </div>
          <form
            className="admissions-ai-form"
            onSubmit={(event) => {
              event.preventDefault();
              void run(async () => {
                setContext(
                  await request<Context>(`/conversations/${selected}/context`, {
                    method: "POST",
                    body: JSON.stringify({
                      question,
                      program_id: programId ? Number(programId) : null,
                      semester: Number(semester) || 1,
                    }),
                  }),
                );
              });
            }}
          >
            <div className="field">
              <label htmlFor="admissions-program">
                Programa ofrecido · selección exacta opcional
              </label>
              <select
                id="admissions-program"
                value={programId}
                disabled={busy}
                onChange={(event) => {
                  setProgramId(event.target.value);
                  setPreviewConversation("");
                  setPreview(null);
                  setContext(null);
                }}
              >
                <option value="">
                  Resolver desde la pregunta o consultar oferta general
                </option>
                {academic?.items.map((program) => (
                  <option key={program.program_id} value={program.program_id}>
                    {program.name} · {program.modality} · {program.schedule} ·
                    ID {program.program_id}
                  </option>
                ))}
              </select>
            </div>
            {academic?.has_more && (
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    const next = await request<AcademicCatalog>(
                      `/institutional/programs?offset=${academic.items.length}`,
                    );
                    setAcademic({
                      ...next,
                      items: [...academic.items, ...next.items],
                    });
                  })
                }
              >
                Cargar más programas de la oferta
              </Button>
            )}
            <Field
              id="admissions-semester"
              label="Semestre o nivel consultado · primer semestre por defecto"
              type="number"
              min={1}
              max={12}
              value={semester}
              onChange={(event) => {
                setSemester(event.target.value);
                setPreviewConversation("");
                setPreview(null);
                setContext(null);
              }}
            />
            <TextArea
              id="memory-context-question"
              label="Pregunta para revisar el contexto"
              rows={3}
              maxLength={2000}
              value={question}
              onChange={(event) => {
                setQuestion(event.target.value);
                if (!programId) setPreviewConversation("");
              }}
            />
            <Button type="submit" disabled={busy || !question.trim()}>
              Ver prompt y fuentes sin generar respuesta
            </Button>
            <p className="muted">
              Consulte la información académica y los documentos institucionales
              disponibles.
            </p>
            <div className="form-actions">
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => void run(loadPreviewModels)}
              >
                Cargar modelos
              </Button>
            </div>
            <div className="field">
              <label htmlFor="admissions-preview-model">
                Modelo{previewProvider ? ` · ${previewProvider}` : ""}
              </label>
              <select
                id="admissions-preview-model"
                value={previewModel}
                disabled={busy}
                onChange={(event) => {
                  setPreviewModel(event.target.value);
                  setPreviewConversation("");
                  setPreview(null);
                }}
              >
                <option value="">Usar modelo actual</option>
                {previewModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.id}
                  </option>
                ))}
              </select>
              <p className="muted">Selección temporal.</p>
            </div>
            <Button
              variant="secondary"
              disabled={busy || !question.trim()}
              onClick={() => void run(generatePreview)}
            >
              {busy ? "Procesando…" : "Generar respuesta y voz"}
            </Button>
          </form>
        </>
      )}
      {preview && (
        <section
          className="admissions-document"
          aria-label="Respuesta de admisiones"
        >
          <h3>Respuesta · {preview.model}</h3>
          <p>
            Proveedor: {preview.provider} · Voz: {preview.voice_provider} ·{" "}
            {preview.voice_status === "generated"
              ? "Audio generado"
              : preview.voice_status === "disabled"
                ? "Voz desactivada"
                : preview.voice_status === "limit_reached"
                  ? "Límite de voz alcanzado"
                  : preview.voice_status === "failed_text_preserved"
                    ? "No se pudo generar audio; texto conservado"
                    : "Respuesta de texto"}
          </p>
          <Notice>
            Período {preview.institutional.period.label}
            {preview.institutional.selected_program
              ? ` · ${preview.institutional.selected_program.name} · ${preview.institutional.selected_program.schedule}`
              : " · consulta general, seleccione programa para detalles"}
            {preview.documents_missing
              ? " · sin documentos complementarios coincidentes"
              : " · con documentos complementarios"}
            .
          </Notice>
          <p>{preview.text}</p>
          {preview.audio_id && <AudioReply identifier={preview.audio_id} />}
          {preview.voice_error && (
            <p role="status">Detalle de voz: {preview.voice_error}</p>
          )}
          <p>{preview.admissions_sources.length} fuentes recuperadas.</p>
          {preview.admissions_sources.map((source) => (
            <p key={source.id}>
              {source.title}
              {source.page ? ` · página ${source.page}` : ""} · {source.id}
            </p>
          ))}
        </section>
      )}
      {context && (
        <details open className="admissions-context">
          <summary>Contexto ensamblado</summary>
          <p>{context.sources.length} fuentes institucionales recuperadas.</p>
          {context.messages.map((message, index) => (
            <div key={index}>
              <h3>
                {message.role === "system"
                  ? "Sistema y política"
                  : index === 1
                    ? "Fuentes, memoria e historial"
                    : "Pregunta actual"}
              </h3>
              <pre>{message.content}</pre>
            </div>
          ))}
        </details>
      )}
    </section>
  );
}
