"""Explicit contact requests shared by campaigns and reply scheduling."""

import unicodedata
import re


def opted_out(text):
    if not isinstance(text, str):
        return False
    value = "".join(ch for ch in unicodedata.normalize("NFKD", text).casefold()
                    if not unicodedata.combining(ch))
    value = re.sub(r"\s+", " ", value).strip(" .!?,;:\r\n\t")
    return value in {
        "stop", "baja", "unsubscribe", "cancelar suscripcion", "darme de baja",
        "no recibir mensajes", "pausa", "prefiero pausa", "pausar seguimiento",
        "pausar el seguimiento", "prefiero dejar el seguimiento en pausa",
        "dejemos el seguimiento en pausa", "no mas mensajes", "no contactar",
    } or bool(re.search(
        r"(?:^|[.!;,]\s*)(?:por favor[, ]+)?(?:"
        r"no (?:quiero|deseo) (?:(?:seguir|mas) )?(?:recibir )?(?:mas )?(?:mensajes|publicidad|promociones)\b|"
        r"no (?:quiero|deseo) (?:seguir )?recibir (?:mas )?informacion\b|"
        r"no (?:quiero|deseo) que me (?:escriban|contacten|llamen|envien|manden)\b|"
        r"no me (?:contacten|escriban|llamen|envien|manden)\b|"
        r"(?:dejen|deja) de (?:escribirme|contactarme|llamarme|mandarme mensajes|enviarme mensajes)\b|"
        r"(?:elimin(?:en|a)me|borrenme|retirenme) de (?:su |la |esta )?(?:lista|base de datos)\b|"
        r"no contactar\b)", value)) or bool(re.fullmatch(
            r"¿?(?:pueden|podrian|puedes|podrias) (?:por favor )?dejar de (?:escribirme|contactarme|enviarme mensajes)(?: por favor)?[? ]*", value))
