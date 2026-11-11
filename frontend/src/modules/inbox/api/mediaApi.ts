export type InboxMedia = {
  id: string;
  state: string;
  kind: "image" | "audio" | "document" | null;
  name: string;
  mime: string | null;
  size: number | null;
  duration: number | null;
  error: string | null;
};

const messages: Record<string, string> = {
  media_size_limit: "El archivo supera el límite de 5 MB.",
  media_storage_quota:
    "Se alcanzó el espacio disponible para archivos. Descarte adjuntos pendientes o contacte al administrador.",
  media_audio_duration_limit: "El audio debe durar como máximo 5 minutos.",
  media_type_unsupported:
    "Formato no admitido. Use JPEG, PNG, PDF, TXT, Office sin macros o un archivo de audio compatible.",
  media_document_active:
    "Este PDF está cifrado o contiene elementos activos no admitidos. Use un PDF sin cifrado, acciones ni archivos incrustados.",
  media_document_invalid:
    "No se pudo validar la estructura del documento. Exporte nuevamente un PDF válido.",
  media_document_limit:
    "El PDF supera los límites seguros de complejidad, descompresión o tiempo de inspección. Exporte una versión simplificada.",
  media_office_invalid:
    "El documento Office no es válido o incluye macros, vínculos externos o contenido incrustado no admitido.",
  media_image_invalid:
    "No se pudo validar la imagen. Use un JPEG o PNG válido de hasta 16 megapíxeles.",
  media_audio_invalid:
    "No se pudo validar o convertir este audio. Use una grabación de audio válida.",
  media_inspection_failed: "No se pudo completar la validación del archivo.",
  media_inspector_unavailable:
    "La validación multimedia no está disponible en este momento.",
  media_not_ready_or_used:
    "El adjunto no está listo o ya pertenece a un mensaje. Actualice la conversación.",
  media_operation_in_progress:
    "La carga anterior sigue en curso. Actualice el adjunto antes de volver a cargarlo.",
  media_operation_changed:
    "El adjunto cambió. Actualice su estado; el borrador se conserva.",
  media_expired:
    "El adjunto pendiente venció. Seleccione el archivo nuevamente.",
  media_not_found: "El adjunto ya no está disponible.",
  media_content_unavailable: "El archivo privado no está disponible.",
  channel_media_not_supported:
    "La subida de archivos no está habilitada para este canal.",
  media_caption_unsupported:
    "Envíe este adjunto sin texto adicional y escriba el texto en otro mensaje.",
  instagram_page_media_required:
    "Instagram requiere conexión por Facebook Login con Page ID y Page Access Token para subir archivos de forma privada.",
  tiktok_image_limit:
    "TikTok solo admite imágenes JPEG/PNG de hasta 3 MB, sin texto en el mismo mensaje.",
  human_open_conversation_required:
    "Tome control humano y abra la conversación antes de adjuntar archivos.",
};

function url(conversation: string, id: string, content = false) {
  return `/api/local/crm/inbox/conversations/${encodeURIComponent(conversation)}/media/${encodeURIComponent(id)}${content ? "/content" : ""}`;
}
async function checked(response: Response) {
  if (!response.ok) {
    const value = await response.json().catch(() => ({}));
    throw new Error(
      messages[value.detail ?? value.code] ??
        "No se pudo completar la operación del adjunto. El borrador se conserva.",
    );
  }
  return response;
}
export const mediaApi = {
  async upload(
    conversation: string,
    id: string,
    file: File,
    signal: AbortSignal,
  ): Promise<InboxMedia> {
    return (
      await checked(
        await fetch(url(conversation, id), {
          method: "PUT",
          headers: {
            "X-CRM-Local": "1",
            "Content-Type": "application/octet-stream",
            "X-CRM-Filename": encodeURIComponent(file.name),
          },
          body: file,
          signal: AbortSignal.any([signal, AbortSignal.timeout(70000)]),
          cache: "no-store",
        }),
      )
    ).json();
  },
  async read(
    conversation: string,
    id: string,
    signal?: AbortSignal,
  ): Promise<InboxMedia> {
    return (
      await checked(
        await fetch(url(conversation, id), {
          headers: { "X-CRM-Local": "1" },
          signal,
          cache: "no-store",
        }),
      )
    ).json();
  },
  async discard(conversation: string, id: string) {
    await checked(
      await fetch(url(conversation, id), {
        method: "DELETE",
        headers: { "X-CRM-Local": "1" },
        cache: "no-store",
      }),
    );
  },
  async blob(
    conversation: string,
    id: string,
    signal?: AbortSignal,
  ): Promise<Blob> {
    return (
      await checked(
        await fetch(url(conversation, id, true), {
          headers: { "X-CRM-Local": "1" },
          signal,
          cache: "no-store",
        }),
      )
    ).blob();
  },
};
