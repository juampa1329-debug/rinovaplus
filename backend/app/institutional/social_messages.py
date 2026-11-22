"""Typed presentation of provider events; never treat a mention as customer text."""


def presentation(provider):
    if not isinstance(provider, dict):
        return None
    message = provider.get("message") or {}
    if not isinstance(message, dict):
        return None
    attachments = message.get("attachments") or []
    kinds = {a.get("type") for a in attachments if isinstance(a, dict)}
    if "story_mention" in kinds:
        return {"kind": "story_mention", "label": "Te mencionó en una historia", "temporary": True}
    if isinstance(message.get("reply_to"), dict) and message["reply_to"].get("story"):
        return {"kind": "story_reply", "label": "Respondió a una historia", "temporary": True}
    for kind, label in [("ig_post", "Compartió una publicación"), ("share", "Compartió contenido"),
                        ("image", "Foto"), ("video", "Video"), ("audio", "Audio"), ("file", "Documento")]:
        if kind in kinds:
            return {"kind": kind, "label": label, "temporary": False}
    return None


def text(message):
    value = presentation({"message": message})
    return message.get("text") or (value["label"] if value else "[multimedia]")
