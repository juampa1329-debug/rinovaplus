"""Evidence-based commercial signals, never calibrated probabilities."""

import json
from typing import Annotated, Literal

from pydantic import Field, StrictBool, model_validator

from app.modules.conversation_analysis.domain.models import redact, validate_context
from app.modules.inbox.application.operations import Write
from app.schemas import LocalModel
from app.sql_workspace import Identifier

STRATEGY_VERSION = "strategy-v1"
STRATEGY_PROMPT = """
Devuelve un objeto con context (las seis listas indicadas) y strategy.
strategy tiene signals (máximo tres objetos: criterion, text, evidenceIds),
churn (level: unknown, concern o withdrawal; text; evidenceIds),
noContact (booleano), noContactEvidenceIds, recommendations, objections,
remarketing y drafts (cada lista máximo tres objetos text/evidenceIds).
criterion sólo interest, next_step o commitment. Cada señal requiere una
declaración entrante comprobable. No calcules probabilidades ni puntuaciones.
No-contacto requiere evidencia entrante explícita: conserva cualquier solicitud
previa de no contacto o retirada de consentimiento. Una objeción no prueba
abandono; outgoing, silencio y feedback humano no prueban intención del contacto.
Sin evidencia entrante: signals vacía, churn unknown, no planes ejecutables.
Recomendaciones y remarketing son propuestas, nunca campañas enviadas.
Usa persuasión informativa, no presión, e identifica las objeciones por evidencia.
No inventes horarios, fechas acordadas, precios, programas o políticas.
Los borradores no se envían. Cada texto máximo 400 caracteres, referencias
opacas presentes en la entrada. No incluyas datos personales.
"""


class EvidenceText(LocalModel):
    text: Annotated[str, Field(min_length=1, max_length=400)]
    evidenceIds: Annotated[list[Identifier], Field(min_length=1, max_length=8)]

    @model_validator(mode="after")
    def meaningful(self):
        self.text = self.text.strip()
        if not self.text:
            raise ValueError("Evidence text required")
        return self


class Signal(EvidenceText):
    criterion: Literal["interest", "next_step", "commitment"]


class Churn(LocalModel):
    level: Literal["unknown", "concern", "withdrawal"]
    text: Annotated[str, Field(max_length=400)]
    evidenceIds: Annotated[list[Identifier], Field(max_length=8)]


Items = Annotated[list[EvidenceText], Field(max_length=3)]


class StrategyDocument(LocalModel):
    version: Literal["strategy-v1"] = STRATEGY_VERSION
    signals: Annotated[list[Signal], Field(max_length=3)]
    churn: Churn
    noContact: StrictBool
    noContactEvidenceIds: Annotated[list[Identifier], Field(max_length=8)]
    recommendations: Items
    objections: Items
    remarketing: Items
    drafts: Items

    @model_validator(mode="after")
    def coherent(self):
        criteria = [s.criterion for s in self.signals]
        if len(criteria) != len(set(criteria)):
            raise ValueError("Duplicate criterion")
        if self.churn.level != "unknown" and not self.churn.evidenceIds:
            raise ValueError("Churn evidence required")
        self.churn.text = self.churn.text.strip()
        if self.churn.level != "unknown" and not self.churn.text:
            raise ValueError("Churn explanation required")
        if self.noContact and not self.noContactEvidenceIds:
            raise ValueError("No-contact evidence required")
        return self


class AutonomyWrite(Write):
    enabled: StrictBool


class PauseWrite(Write):
    paused: StrictBool


class StrategyFeedbackWrite(Write):
    planId: Identifier
    planRevision: Annotated[int, Field(ge=1)]
    usefulness: Literal["useful", "not_useful", "correction"]
    outcome: Literal["not_observed", "followup_needed", "reply_observed", "no_contact"]
    correction: Annotated[str, Field(max_length=1000)] = ""

    @model_validator(mode="after")
    def correction_required(self):
        self.correction = self.correction.strip()
        if self.usefulness == "correction" and not self.correction:
            raise ValueError("Correction required")
        return self


def validate_result(raw, references, known=()):
    """Accept legacy contexts, but never manufacture a legacy commercial plan."""
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Invalid analysis result")
    if "context" not in value:
        return validate_context(raw, references, known), None
    if set(value) != {"context", "strategy"}:
        raise ValueError("Invalid analysis envelope")
    context = validate_context(json.dumps(value["context"]), references, known)
    document = value["strategy"]
    if not isinstance(document, dict):
        raise ValueError("Invalid strategy")
    for key in ("signals", "recommendations", "objections", "remarketing", "drafts"):
        if not isinstance(document.get(key), list):
            raise ValueError("Invalid strategy list")
        for item in document[key]:
            aliases = item.get("evidenceIds") if isinstance(item, dict) else None
            ids, has_incoming = resolve(aliases, references)
            if key == "signals" and not has_incoming:
                raise ValueError("Signals require incoming evidence")
            item["evidenceIds"] = ids
            item["text"] = redact(item.get("text", ""), known)
    churn = document.get("churn")
    if not isinstance(churn, dict):
        raise ValueError("Invalid churn")
    ids, supported = resolve(churn.get("evidenceIds"), references, allow_empty=True)
    if (
        churn.get("level") != "unknown" or churn.get("text", "").strip()
    ) and not supported:
        raise ValueError("Churn requires incoming evidence")
    churn["evidenceIds"] = ids
    churn["text"] = redact(churn.get("text", ""), known)
    ids, supported = resolve(document.get("noContactEvidenceIds"), references, True)
    if document.get("noContact") and not supported:
        raise ValueError("No-contact requires incoming evidence")
    document["noContactEvidenceIds"] = ids
    result = StrategyDocument.model_validate(document).model_dump()
    # Plans without contact evidence remain readable, but cannot execute.
    result["index"] = len(result["signals"]) if result["signals"] else None
    result["followupSupported"] = (
        any(s["criterion"] in ("next_step", "commitment") for s in result["signals"])
        and not result["noContact"]
        and result["churn"]["level"] != "withdrawal"
    )
    return context, result


def resolve(aliases, references, allow_empty=False):
    if not isinstance(aliases, list) or (not aliases and not allow_empty):
        raise ValueError("Evidence required")
    if any(not isinstance(a, str) or a not in references for a in aliases):
        raise ValueError("Unsupported evidence")
    return list(dict.fromkeys(str(references[a][0]).lower() for a in aliases)), any(
        references[a][1] == "incoming" for a in aliases
    )
