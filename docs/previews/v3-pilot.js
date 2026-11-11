"use strict";

// Independent visual fixtures transcribed from the application's seed data.
// The preview never reads or writes application state, storage or APIs.
const seed = [
  { id: "demo-1", name: "Persona Demo A", channel: "WhatsApp", unread: true, mode: "ai", stage: "Interés", program: "Auxiliar administrativo · Demo", schedule: "Nocturna · Demo", tags: "Solicita asesoría", type: "Prospecto", interests: "Programa y jornada", notes: "Consultar el programa y la jornada. Caso ficticio.", messages: [
    { body: "Hola. Quiero conocer el programa de auxiliar administrativo.", direction: "incoming" },
    { body: "Soy el asistente virtual de demostración. Un asesor puede orientarle sobre la jornada.", direction: "outgoing" },
    { body: "Me interesa la jornada. Prefiero conversar con un asesor.", direction: "incoming" }
  ] },
  { id: "demo-2", name: "Persona Demo B", channel: "Facebook", unread: false, mode: "human", stage: "Solicitud preparada", program: "Atención a la primera infancia · Demo", schedule: "Diurna · Demo", tags: "Formulario", type: "Prospecto", interests: "Inscripción", notes: "Revisar los campos antes de continuar. Caso ficticio.", messages: [{ body: "Quiero inscribirme. Quisiera revisar el formulario antes de continuar.", direction: "incoming" }] },
  { id: "demo-3", name: "Persona Demo C", channel: "Instagram", unread: true, mode: "ai", stage: "Nuevo", program: "Asistencia contable · Demo", schedule: "Sabatina · Demo", tags: "Contacto nuevo", type: "Contacto", interests: "Jornada", notes: "", messages: [{ body: "Ya no me interesa la jornada sabatina. No continuaré.", direction: "incoming" }] },
  { id: "demo-4", name: "Persona Demo D", channel: "TikTok", unread: false, mode: "human", stage: "Contactado", program: "Auxiliar administrativo · Demo", schedule: "Diurna · Demo", tags: "Seguimiento", type: "Contacto", interests: "", notes: "Sin acción externa programada.", messages: [{ body: "Mensaje saliente ficticio. No hay respuesta recibida.", direction: "outgoing" }] }
];
const commentSeed = [
  { author: "Perfil Demo A", platform: "Facebook", post: "Publicación ficticia: orientación sobre programas", body: "¿Dónde puedo conocer las jornadas?", status: "Pendiente" },
  { author: "Perfil Demo B", platform: "Instagram", post: "Publicación ficticia: recorrido de admisiones", body: "Me gustaría recibir información del formulario.", status: "Pendiente" },
  { author: "Perfil Demo C", platform: "TikTok", post: "Video ficticio: conoce la experiencia académica", body: "¿Hay atención de un asesor?", status: "Respondido" }
];
const modules = [["clients", "Clientes y prospectos"], ["application", "Formulario de aspirante"], ["review", "Revisión académica"], ["assistant", "Asistente"], ["knowledge", "Conocimiento"], ["memory", "Memoria"], ["settings", "Ajustes e integraciones"], ["access", "Acceso y permisos"], ["retention", "Retención"], ["corporate", "Corporativo"], ["creators", "Creadores · Referencia"]];
const stages = ["Nuevo", "Contactado", "Interés", "Solicitud preparada"];
const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
let records = structuredClone(seed);
let selectedId = "demo-1";
let drafts = {};
let contextVisible = false;
let currentPage = "overview";
let inboxMode = "messages";

function announce(text) { $("feedback").textContent = text; }
function selected() { return records.find((item) => item.id === selectedId); }
function isMobile() { return window.matchMedia("(max-width: 703px)").matches; }
function focusElement(id) { $(id).focus({ preventScroll: true }); }
function setMobilePanel(panel) { $("messages-view").dataset.mobilePanel = panel; }

$("other-navigation").innerHTML = modules.map(([path, label]) => `<a href="http://127.0.0.1:5173/#/${path}" target="_blank" rel="noopener">${label}</a>`).join("");

function renderOverview() {
  const unread = records.filter((item) => item.unread).length;
  $("metric-clients").textContent = records.length;
  $("metric-unread").textContent = unread;
  $("metric-open").textContent = records.length;
  $("nav-unread").textContent = unread;
  $("pipeline-total").textContent = `${records.length} contactos`;
  $("donut-total").textContent = records.length;
  $("legend-open").textContent = records.length;
  $("status-donut").setAttribute("aria-label", `${records.length} abiertas, 0 en espera y 0 cerradas`);
  $("donut-value").style.display = records.length ? "" : "none";
  $("stage-chart").innerHTML = stages.map((stage) => {
    const count = records.filter((item) => item.stage === stage).length;
    const width = records.length ? count / records.length * 100 : 0;
    return `<div class="stage-row"><span>${stage}</span><div class="bar-track" aria-hidden="true"><div class="bar-value" style="width:${width}%"></div></div><strong>${count}</strong></div>`;
  }).join("");
  $("overview-queue").innerHTML = records.map((item) => `<li class="queue-row"><div class="queue-person"><span class="avatar" aria-hidden="true">${item.id.slice(-1).replace("1", "A").replace("2", "B").replace("3", "C").replace("4", "D")}</span><div><strong>${escapeHtml(item.name)}</strong><p>${escapeHtml(item.messages.at(-1).body)}</p></div></div><span class="queue-channel">${item.channel}</span><span class="badge ${item.mode === "human" ? "success" : "accent"}">${item.mode === "human" ? "Control humano" : "Asistente simulado"}</span><button type="button" class="text-button" data-open-thread="${item.id}" aria-label="Abrir hilo de ${escapeHtml(item.name)}">Abrir <span aria-hidden="true">→</span></button></li>`).join("");
  $("overview-empty").hidden = records.length > 0;
  document.querySelector(".queue-labels").hidden = !records.length;
  $("messages-count").textContent = records.length;
  document.querySelector('[data-inbox-mode="comments"] span').textContent = records.length ? commentSeed.length : 0;
}

function matchingRecords() {
  const query = $("search").value.trim().toLocaleLowerCase("es");
  const quick = $("quick-view").value;
  return records.filter((item) => {
    const quickMatch = quick === "Todos" || quick === "Sin asignar" || (quick === "Sin leer" && item.unread) || (quick === "Humano" && item.mode === "human") || (quick === "IA" && item.mode === "ai");
    return [item.name, `DEMO-00${item.id.slice(-1)}`, item.messages.at(-1).body].join(" ").toLocaleLowerCase("es").includes(query)
      && quickMatch && ($("channel").value === "Todos" || $("channel").value === item.channel)
      && ["Todos", "Abierta"].includes($("operational-state").value);
  });
}

function renderList() {
  const visible = matchingRecords();
  $("visible-count").textContent = visible.length;
  $("thread-records").innerHTML = visible.map((item) => `<li><button type="button" class="thread-record" aria-pressed="${item.id === selectedId}" data-select-thread="${item.id}"><span class="thread-name"><strong>${escapeHtml(item.name)}</strong>${item.unread ? '<span class="unread-label">Sin leer</span>' : ""}</span><p>${escapeHtml(item.messages.at(-1).body)}</p><small>${item.channel} · ${item.mode === "human" ? "Control humano" : "IA simulada"}</small><small>Abierta · Sin asignar · Normal</small></button></li>`).join("");
  $("list-empty").hidden = visible.length > 0 || records.length === 0;
  $("dataset-empty").hidden = records.length > 0;
  const secondary = Number($("channel").value !== "Todos") + Number($("operational-state").value !== "Todos");
  $("filter-count").textContent = secondary ? `(${secondary})` : "";
}

function updateComposer() {
  const item = selected();
  const body = $("message-draft").value;
  $("add-message").disabled = !item || item.mode !== "human" || !body.trim() || body.trim().length > 1500;
  $("composer-help").textContent = item?.mode === "human" ? "Añade texto únicamente a esta muestra. No existe envío." : "Tome control humano para añadir un mensaje. La IA no responde.";
}

function renderThread() {
  const item = selected();
  $("thread-content").hidden = !item;
  $("no-thread").hidden = Boolean(item);
  if (!item) { setContext(false, false); return; }
  $("conversation-title").textContent = item.name;
  $("thread-avatar").textContent = "ABCD"[Number(item.id.slice(-1)) - 1];
  $("thread-channel").textContent = `${item.channel} · Abierta`;
  $("control-status").textContent = item.mode === "human" ? "Control humano · Demo" : "Asistente virtual · Simulado";
  $("control-status").className = `badge ${item.mode === "human" ? "success" : "accent"}`;
  $("take-control").textContent = item.mode === "human" ? "Devolver a IA simulada" : "Tomar control";
  $("take-control").classList.toggle("primary", item.mode !== "human");
  $("mark-read").disabled = !item.unread;
  $("mark-read").textContent = item.unread ? "Marcar leído" : "Ya leído";
  $("message-log").innerHTML = '<p class="log-note">Conversación ficticia · Sin conexión al canal</p>' + item.messages.map((message) => `<div class="message ${message.direction}"><p>${escapeHtml(message.body)}</p><small>${message.direction === "incoming" ? "Contacto ficticio" : "Respuesta local · No enviada"}</small></div>`).join("");
  $("message-draft").value = drafts[item.id] || "";
  renderContext(item);
  updateComposer();
}

function renderContext(item) {
  const fields = [["Programa", item.program], ["Jornada", item.schedule], ["Etiqueta", item.tags], ["Tipo", item.type], ["Intereses", item.interests || "Sin definir"], ["Correo de ejemplo", "Sin definir"], ["Notas", item.notes || "Sin notas locales"]];
  $("context-content").innerHTML = `<div class="context-identity"><span class="avatar" aria-hidden="true">${"ABCD"[Number(item.id.slice(-1)) - 1]}</span><h3>${escapeHtml(item.name)}</h3><span class="badge accent">${item.stage}</span></div><dl class="context-fields">${fields.map(([label, value]) => `<dt>${label}</dt><dd>${escapeHtml(value)}</dd>`).join("")}</dl><div class="context-section"><strong>Análisis y seguimiento</strong><p>Ubicación propuesta para mini CRM, tareas humanas y cronología. Se conservan en la app actual.</p></div><a class="context-link" href="http://127.0.0.1:5173/#/clients" target="_blank" rel="noopener">Abrir Clientes en la app actual</a><p class="small muted">El enlace abre Clientes; no transfiere cambios ni selección desde esta muestra.</p>`;
}

function setContext(visible, moveFocus = true) {
  contextVisible = visible;
  $("contact-context").hidden = !visible;
  $("messages-view").classList.toggle("context-open", visible);
  $("show-context").setAttribute("aria-expanded", String(visible));
  $("show-context").textContent = visible ? "Ocultar ficha" : "Ver ficha";
  if (isMobile()) setMobilePanel(visible ? "context" : "thread");
  if (moveFocus) {
    const targetId = visible ? "context-title" : "show-context";
    focusElement(targetId);
    const bounds = $(targetId).getBoundingClientRect();
    if (bounds.top < 0 || bounds.bottom > window.innerHeight) {
      $(targetId).scrollIntoView({ block: "nearest", behavior: "instant" });
    }
  }
}

function openThread(id) {
  selectedId = id;
  setContext(false, false);
  inboxMode = "messages";
  renderInboxMode();
  renderList();
  renderThread();
  setMobilePanel("thread");
  if (currentPage !== "inbox") { location.hash = "inbox"; }
  else { focusElement("conversation-title"); }
}

function renderComments() {
  $("comments-list").innerHTML = records.length ? commentSeed.map((item) => `<article><div class="comment-heading"><h3>${item.author} <span class="muted">· ${item.platform}</span></h3><span class="badge ${item.status === "Respondido" ? "success" : ""}">${item.status}</span></div><small class="muted">${item.post}</small><p>${item.body}</p>${item.status === "Respondido" ? '<p class="small muted">Respuesta ficticia de ejemplo. No publicada.</p>' : ""}</article>`).join("") : '<div class="empty-state"><h3>No hay comentarios en este escenario</h3><p>Seleccione Habitual para recuperar las tres muestras ficticias.</p><button type="button" data-reset-scenario>Ver casos de ejemplo</button></div>';
}

function renderInboxMode() {
  $("messages-view").hidden = inboxMode !== "messages";
  $("comments-view").hidden = inboxMode !== "comments";
  document.querySelectorAll("[data-inbox-mode]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.inboxMode === inboxMode)));
}

function route(moveFocus = true) {
  currentPage = location.hash === "#inbox" ? "inbox" : "overview";
  $("overview-view").hidden = currentPage !== "overview";
  $("inbox-view").hidden = currentPage !== "inbox";
  $("page-title").textContent = currentPage === "overview" ? "Resumen de admisiones" : "Conversaciones";
  $("page-subtitle").textContent = currentPage === "overview" ? "Cada conversación, con su siguiente paso a la vista." : "Atención humana y contexto, en el mismo lugar.";
  document.querySelectorAll("[data-page]").forEach((link) => {
    if (link.dataset.page === currentPage) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  announce("");
  if (moveFocus) {
    window.scrollTo(0, 0);
    focusElement("page-title");
  }
}

function resetFilters() {
  $("search").value = "";
  $("quick-view").value = "Todos";
  $("channel").value = "Todos";
  $("operational-state").value = "Todos";
  renderList();
}

function resetScenario() {
  records = $("scenario").value === "empty" ? [] : structuredClone(seed);
  if ($("scenario").value === "long") {
    records[0].name = "Persona Demo A con nombre extenso para comprobar lectura y distribución";
    records[0].messages.push({ direction: "incoming", body: "Estoy revisando las alternativas de jornada del programa ficticio y quisiera confirmar cuáles son los pasos para preparar mi solicitud. También necesito que un asesor revise conmigo la información antes de continuar. Referencia ficticia extensa: DEMO_" + "CONTEXTO".repeat(14) });
    records[0].notes = "Caso de estrés visual. Nombre y mensaje deliberadamente extensos; no representan un cambio de información del CRM ni datos de una persona real.";
  }
  selectedId = records[0]?.id || "";
  drafts = {};
  resetFilters();
  setContext(false, false);
  setMobilePanel("list");
  renderOverview(); renderThread(); renderComments();
  if (!records.length) setMobilePanel("list");
  announce("Escenario actualizado. Solo se restablecieron los casos y borradores de este piloto.");
}

document.addEventListener("click", (event) => {
  const target = event.target.closest("button, a");
  if (!target) return;
  if (target.dataset.themeChoice) {
    document.documentElement.dataset.theme = target.dataset.themeChoice;
    document.querySelectorAll("[data-theme-choice]").forEach((button) => button.setAttribute("aria-pressed", String(button === target)));
  }
  if (target.dataset.openThread || target.dataset.selectThread) openThread(target.dataset.openThread || target.dataset.selectThread);
  if (target.dataset.inboxMode) { inboxMode = target.dataset.inboxMode; renderInboxMode(); }
  if (target.hasAttribute("data-reset-scenario")) { $("scenario").value = "standard"; resetScenario(); focusElement("page-title"); }
  if (target.dataset.page === "inbox" && isMobile()) setMobilePanel("list");
});
$("scenario").addEventListener("change", resetScenario);
$("search").addEventListener("input", renderList);
["quick-view", "channel", "operational-state"].forEach((id) => $(id).addEventListener("change", renderList));
["reset-filters", "empty-reset"].forEach((id) => $(id).addEventListener("click", () => { resetFilters(); focusElement("search"); }));
$("unread-link").addEventListener("click", () => { resetFilters(); $("quick-view").value = "Sin leer"; renderList(); setMobilePanel("list"); });
$("show-context").addEventListener("click", () => setContext(!contextVisible));
$("close-context").addEventListener("click", () => setContext(false));
$("back-list").addEventListener("click", () => { setContext(false, false); setMobilePanel("list"); focusElement("list-title"); });
$("take-control").addEventListener("click", () => {
  const item = selected();
  if (!item) return;
  item.mode = item.mode === "human" ? "ai" : "human";
  renderThread(); renderList(); renderOverview();
  announce("Control actualizado solo en la muestra. No se ejecuta IA ni coordinación externa.");
});
$("mark-read").addEventListener("click", () => {
  const item = selected();
  if (!item) return;
  item.unread = false;
  renderList(); renderThread(); renderOverview();
  announce("Hilo marcado como leído únicamente en el piloto.");
});
$("message-draft").addEventListener("input", () => { drafts[selectedId] = $("message-draft").value; updateComposer(); });
$("composer").addEventListener("submit", (event) => {
  event.preventDefault();
  const item = selected();
  const body = $("message-draft").value.trim();
  if (!item || item.mode !== "human" || !body || body.length > 1500) return;
  item.messages.push({ body, direction: "outgoing" });
  drafts[selectedId] = "";
  renderThread(); renderList(); renderOverview();
  announce("Mensaje añadido a esta muestra local. No se envió a ningún contacto.");
  focusElement("message-draft");
});
window.addEventListener("hashchange", () => route());
window.matchMedia("(max-width: 703px)").addEventListener("change", () => {
  if (isMobile() && contextVisible) setMobilePanel("context");
  else if (isMobile() && $("messages-view").dataset.mobilePanel !== "list") setMobilePanel("thread");
});
renderOverview(); renderList(); renderThread(); renderComments(); renderInboxMode(); route(false);
