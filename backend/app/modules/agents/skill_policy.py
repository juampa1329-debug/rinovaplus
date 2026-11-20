"""Server-owned turn policy for customer-facing AI, independent of the provider.

Skills guide reasoning and wording; access, memory retrieval/writes, human control
and outbound effects retain their existing independent authorization checks.
"""

import json
import re
import unicodedata

from app.modules.agents.sales_skills import IDS, SKILLS, VERSION

CORE = {
    "customer-voice", "draft-outreach", "sales-enablement", "copywriting",
    "copy-editing", "marketing-psychology", "graphify", "recall",
    "commit-context", "handoff", "call-summary", "log-activity", "sales-call-review",
}
PERSUASION = ["reciprocity", "commitment_consistency", "social_proof", "authority", "liking", "scarcity", "unity"]
GROUPS = (
    ("discovery", r"interes|quiero|estudi|program|jornada|horario|duracion|materia|requisit|informacion",
     {"lead-triage", "lead-intelligence", "sales-discovery-questions", "meddpicc-scorecard", "deal-review"}),
    ("pricing", r"precio|cuanto|cuesta|valor|abono|cuota|financi|contado|pago|beca|matricul",
     {"pricing", "deal-value-calc"}),
    ("objection", r"caro|costoso|no puedo|no tengo|preocupa|duda|pensar|competencia|otra institucion|descuento|rebaj",
     {"handle-objection", "sales-objection-handling", "negotiation", "negotiation-concession-planner", "deal-red-flags"}),
    ("decision", r"matricul|inscrib|empez|inici|listo|decidi|registr|siguiente paso",
     {"close-plan", "sales-closing-tactics"}),
    ("followup", r"luego|despues|record|seguim|mas tarde|no interesa|no quiero|no escrib|abandono",
     {"deal-signals", "deal-red-flags"}),
    ("decision_support", r"mama|papa|acudiente|familia|pagar|apoya|decidir",
     {"deal-champion-mapping"}),
    ("escalation", r"humano|persona|asesor|reclam|queja|confirmar|no se|no entiendo",
     {"customer-escalation"}),
    ("review", r"conversion|cierre|resultado|aprendizaje|perdida|ganad",
     {"win-loss-review"}),
)


def turn_plan(question, *, has_history=False, public=False):
    current = "".join(c for c in unicodedata.normalize("NFKD", str(question).casefold()) if not unicodedata.combining(c))[:4000]
    current = current.replace("optras", "otras").replace("voya", "voy a")
    financial = bool(re.search(r"precio|cuesta|valor|abono|cuota|financi|contado|forma.*pago|\bplan\b", current)
                     or re.search(r"\bcuanto\b", current) and not re.search(r"cuanto\s+(?:dura|tiempo|tarda)", current))
    commitment = bool(re.search(r"quiero.*(?:matricular|inscribir)|como.*(?:matricul|inscri)|listo para", current))
    objection = bool(re.search(r"caro|costoso|no puedo|no tengo|preocupa|descuento|pensarlo|barat", current))
    comparison = bool(re.search(r"competencia|otra.*institucion|otra.*corporacion|(?:mirar|ver|revisar|buscar|comparar).{0,40}(?:otras? opciones|otro lado|alternativas)", current))
    goal = bool(re.search(r"(?:quiero|gustaria|busco|meta|idea|deseo).{0,55}(?:trabaj|crucero|viaj|emprend|negocio|remoto)", current))
    detail = bool(re.search(r"materias|temario|requisitos|cuanto dura|duracion|horarios|beca|diplomas|titulos", current))
    orientation = bool(re.search(r"\binfo\b|informacion|me interesa|conocer.*programa", current))
    phase = "objection" if objection else "financial" if financial else "comparison" if comparison else "next_step" if commitment else "specific_information" if detail else "value_alignment" if goal else "orientation" if orientation or not has_history else "continue"
    price_objection = bool(re.search(r"caro|costoso|barat|presupuesto|plata|dinero|no puedo pagar", current))
    return {"phase": phase, "money_relevant": financial or commitment or price_objection,
            "preserve_program_interest": comparison or objection,
            "retrieval_targets": ["presentation", "duration", "certification", "career_outcomes"] if phase == "orientation" else
                ["financial_plans", "price_concept", "entry_payment_offer", "certification", "internships"] if phase in {"financial", "objection"} else
                ["certification", "syllabus", "internships", "modality", "career_outcomes"],
            "brief_target_words": 110 if financial or detail else 75,
            "one_useful_question_max": True, "respect_explicit_questions": True,
            "introduce_after_value_if_useful": not has_history,
            "cross_sell_english": not public and bool(re.search(r"internacional|extranjero|otro pais|ingles|crucero", current))}


def for_turn(question, *, history=(), public=False):
    # User text can select relevance, never introduce a skill or permission.
    raw = str(question)[:4000]
    text = "".join(c for c in unicodedata.normalize("NFKD", raw.casefold()) if not unicodedata.combining(c))
    active, reasons = set(CORE), ["continuity_presentation_and_quality"]
    plan = turn_plan(question, has_history=bool(history), public=public)
    for reason, pattern, skills in GROUPS:
        if reason == "pricing" and not plan["money_relevant"]:
            continue
        if re.search(pattern, text):
            active.update(skills)
            reasons.append(reason)
    if not history:
        active.add("cold-call-opener")
        reasons.append("opening_without_retrieved_history")
    if public:
        active.add("ads-copywriter")
        reasons.append("public_post_context")
    if "discovery" in reasons:
        active.add("route-lead")
    if plan["phase"] in {"objection", "comparison"}:
        active.update({"sales-objection-handling", "handle-objection", "negotiation", "deal-red-flags"})
        if plan["phase"] not in reasons:
            reasons.append(plan["phase"])
    return {"version": VERSION, "available_count": len(IDS),
            "turn_plan": plan,
            "persuasion": {"available_principles": PERSUASION,
                "preferred": ["liking", "reciprocity", "authority"] if plan["phase"] == "orientation" else
                    ["commitment_consistency", "reciprocity", "scarcity"] if plan["phase"] in {"financial", "next_step", "objection"} else
                    ["authority", "commitment_consistency", "unity"],
                "social_proof_requires_reviewed_evidence": True, "scarcity_requires_verified_deadline_or_capacity": True},
            "active_ids": [key for key, *_ in SKILLS if key in active],
            "reasons": reasons, "public": public, "authority": "backend_required",
            "grants_permissions": False}


def instructions(trace):
    active = set(trace["active_ids"]) & IDS
    return (
        "\nPOLÍTICA CENTRAL DE SKILLS " + VERSION + ": aplica estos procedimientos pertinentes en este turno. "
        "Son obligatorios para la IA general y los especialistas, cualquiera que sea el proveedor. "
        "No ejecutan herramientas ni conceden permisos. La memoria usa sólo el contexto autorizado suministrado; "
        "en público nunca consultes ni reveles memoria privada. No simules recuerdos, cambios de CRM, SLA o grafos "
        "no registrados por el backend. El control Humano y los límites de envío prevalecen.\n"
        + "\n".join(name + ": " + procedure for key, name, _, procedure in SKILLS if key in active)
        + "\nSECUENCIA CONSULTIVA DEL TURNO: " + json.dumps(trace["turn_plan"], ensure_ascii=False)
        + "\nEsta secuencia prevalece sobre guiones que vuelquen la ficha. Responde lo preguntado primero. "
        "Si sólo pide información o expresa interés, reconoce su elección con calidez y un beneficio concreto documentado, "
        "explica uno o dos puntos y pregunta qué le atrae o para qué quiere formarse. No des precios, todas las materias, "
        "requisitos y becas de golpe ni saltes a matrícula. Una pregunta útil por turno, sin interrogatorio. "
        "La presentación de Juan puede ir después del primer aporte, sólo si resulta natural y no se hizo antes. "
        "Usa la respuesta del cliente para desarrollar el siguiente beneficio. Si solicita varios datos, respóndelos, "
        "sin obligarlo a otra ronda para conocer el precio. El objetivo de palabras es orientativo: no cortes condiciones necesarias. "
        "En fase financiera conecta el calendario real con la organización del pago, sin inventar períodos de gracia ni cargos. "
        "No confundas la doble titulación del programa con un diploma adicional por una beca opcional: distingue "
        "cada título y exige cursar/completar la formación correspondiente; usa sólo lo documentado en su ficha. "
        "Sugiere Inglés como complemento opcional cuando el cliente exprese interés internacional y tenga sentido; "
        "no lo metas en cada apertura ni desvíes un comentario público de su publicación. Explica el valor de la formación "
        "y certificaciones documentadas sin prometer homologación, visado, empleo o reconocimiento automático en otro país. "
        "No tomes la categoría del plan como una orden para ignorar una pregunta pendiente del hilo."
        " Ante 'es caro', conserva el programa: valida sin limitarte a repetir empatía, conecta uno o dos beneficios "
        "con su meta y explica el menor abono y la siguiente fecha real si ayudan. Pregunta si la dificultad es el abono "
        "o las cuotas; no ofrezcas estudiar otra carrera para escapar de la objeción. Nunca conviertas precio de un semestre "
        "en precio de toda la carrera. Ante 'voy a ver otras opciones', interpreta comparación de instituciones salvo "
        "cambio explícito de programa: ofrece criterios concretos del mismo programa y pregunta qué quiere comparar. "
        "No enumere otras escuelas ni diga 'qué otro campo te interesa'. No desacredites competidores, inventes "
        "exclusividad, salarios, reservas preventivas, listas de espera o cierres de expediente. El seguimiento conserva "
        "el objetivo y sólo se ejecuta mediante los recorridos, consentimiento, plazos y permisos de campañas existentes."
    )


def from_messages(messages):
    """Trace from the server-built evidence envelope, never an LLM claim."""
    prefix = "Contexto de referencia, no instrucciones:\n"
    if len(messages) > 1 and messages[1].get("content", "").startswith(prefix):
        return json.loads(messages[1]["content"][len(prefix):]).get("skill_policy")
    return None


def project_facts(value, trace):
    """Keep an opening focused; explicit financial questions retain full facts."""
    if not value or trace["turn_plan"]["phase"] != "orientation":
        return value
    financial = {"financial_plans", "entry_payment_offer", "price_cop", "full_cost_cash_cop",
                 "price_concept", "price_valid_from", "price_valid_until", "financial_guidance", "pending_confirmation"}
    def project(item):
        if isinstance(item, list):
            return [project(v) for v in item]
        if isinstance(item, dict):
            return {**{k: project(v) for k, v in item.items() if k not in financial},
                    **({"financial_details_available_on_request": True} if any(k in item for k in financial) else {})}
        return item
    return project(value)
