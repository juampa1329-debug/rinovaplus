"""Explicit CRM fields for template composition; examples never query contacts."""

from fastapi import HTTPException

STANDARD = [
    ("customer_name", "Nombre completo", "Laura Gómez"),
    ("customer_first_name", "Primer nombre", "Laura"),
    ("customer_phone", "Teléfono", "+573000000000"),
    ("customer_email", "Correo", "ejemplo@example.com"),
    ("customer_city", "Ciudad", "Cartagena"),
    ("program", "Programa de interés", "Programa de ejemplo"),
    ("stage", "Etapa CRM", "Nuevo"),
    ("schedule", "Jornada informada", "Jornada de ejemplo"),
    ("campaign_name", "Nombre de campaña", "Información de programas"),
]


def catalog(fields):
    return [
        {"token": key, "label": label, "source": key, "example": example}
        for key, label, example in STANDARD
    ] + [
        {"token": "crm." + f.key, "label": f.label, "source": "custom_field",
         "field_key": f.key, "example": "Ejemplo de " + f.label, "type": f.type}
        for f in fields if f.active
    ]


def bindings(components, variables, token_pattern):
    available = {v["token"]: v for v in variables}
    result = {}
    for component in components:
        kind = component.get("type", "").lower()
        if kind not in {"body", "header"}:
            continue
        names = list(dict.fromkeys(token_pattern.findall(component.get("text", ""))))
        for index, name in enumerate(names, 1):
            if name.isdigit():
                continue  # Imported numeric slots are explicitly mapped in the campaign.
            item = available.get(name)
            if not item:
                raise HTTPException(422, "broadcast_crm_variable_unknown")
            result[f"{kind}.{index}"] = {
                "source": item["source"],
                **({"field_key": item["field_key"]} if item.get("field_key") else {}),
            }
    return result
