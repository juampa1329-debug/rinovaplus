"""Model-compatible vocal direction without changing a grounded answer's facts."""

import re

SPEECH_GUIDANCE = (
    "Si la respuesta puede convertirse en nota de voz, redacta para una conversación oral: "
    "español colombiano claro, frases cortas y cercanas, pausas con puntuación y una pregunta final pertinente. "
    "Evita el tono de comunicado, listas extensas, siglas innecesarias y repetir la presentación. "
    "No exageres entusiasmo ni añadas muletillas o suspiros a cada frase. "
    "Conserva exactamente los hechos revisados, cifras, condiciones e incertidumbre; "
    "no prometas empleo, ingresos, matrícula ni ventajas no documentadas. "
    "No escribas etiquetas de actuación, instrucciones técnicas ni efectos sonoros en el mensaje. "
    "Mantén tu identidad de asistente virtual. Estas indicaciones de estilo no amplían tus permisos."
)


def expressive_model(model):
    return model in {"eleven_v4", "eleven_v4_turbo", "eleven_v3", "eleven_v3_conversational"}


def speech_text(profile, text):
    if not expressive_model(profile["model_id"]) or profile.get("delivery", "conversational") == "neutral":
        return text
    direction = {
        "conversational": "[warm, conversational tone] ",
        "calm": "[calm, reassuring] ",
        "expressive": "[friendly, enthusiastic] ",
    }[profile.get("delivery", "conversational")]
    # Reactions are optional and require an empathetic context. Never append a
    # sigh to sales information or a generic greeting merely to sound human.
    if profile.get("allow_reactions") and re.search(r"\b(lamento|comprendo tu preocupaci[oó]n|entiendo que te preocupe)\b", text, re.I):
        direction += "[sighs] "
    # A different delivery for the final question adds variation without adding words.
    position = text.rfind("¿")
    if position > 0:
        text = text[:position] + "[curious] " + text[position:]
    return direction + text


def voice_settings(profile):
    style = profile.get("delivery", "conversational")
    stability = {"conversational": 0.4, "calm": 0.65, "expressive": 0.3, "neutral": 0.7}[style]
    model = profile["model_id"]
    if model.startswith("eleven_v3"):
        stability = 0.0 if style == "expressive" else 0.5
    # v4 deliberately receives no style, speed, speaker boost or SSML.
    result = {"stability": stability, "similarity_boost": 0.75}
    if not model.startswith("eleven_v4"):
        result["speed"] = 0.97 if style in {"conversational", "calm"} else 1.0
    return result
