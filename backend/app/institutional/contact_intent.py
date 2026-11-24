"""Explicit contact requests shared by campaigns and reply scheduling."""

import unicodedata


def opted_out(text):
    value = unicodedata.normalize("NFKC", text or "").casefold().strip(" .!?,;:\r\n\t")
    return value in {
        "stop", "baja", "unsubscribe", "cancelar suscripción", "darme de baja",
        "no recibir mensajes",
    } or any(part in value for part in ("no me contacten", "no quiero mensajes", "no contactar"))
