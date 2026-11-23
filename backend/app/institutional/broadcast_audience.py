"""Declared CRM segmentation and preparation-time campaign statistics. No inference."""

import json
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException

DIMENSIONS = (
    "gender", "age_band", "city", "region", "country", "program", "schedule",
    "contact_type", "stage", "last_incoming",
)
RECENCY_LABELS = {
    "unknown": "Sin mensaje recibido verificable",
    "0_29": "0–29 días", "30_59": "30–59 días", "60_89": "60–89 días",
    "90_plus": "90 días o más",
}


def incoming_bucket(person, document, as_of):
    """Provider-observed inbound date only; registration/management is not contact."""
    value = person.get("LastIncomingAt")
    try:
        stamp = (
            value if isinstance(value, datetime)
            else datetime.fromisoformat(value.replace("Z", "+00:00"))
        )
        stamp = stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp
        zone = ZoneInfo(document.get("timezone", "America/Bogota"))
        days = (as_of - stamp.astimezone(zone).date()).days
        if days < 0:
            return "unknown"
        for limit, bucket in [(30, "0_29"), (60, "30_59"), (90, "60_89")]:
            if days < limit:
                return bucket
        return "90_plus"
    except (AttributeError, TypeError, ValueError, OverflowError):
        return "unknown"


def normalized(value):
    text = str(value).strip().casefold()
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def gender(value):
    if not isinstance(value, str):
        return "Sin dato"
    key = normalized(value)
    if key in {"hombre", "masculino", "male", "m"}:
        return "Hombre"
    if key in {"mujer", "femenino", "female", "f"}:
        return "Mujer"
    return str(value).strip()[:100] or "Sin dato"


def configuration(document, fields):
    active = {f.key: f for f in fields if f.active}
    mapping = document.get("demographic_fields", {})
    requested = set(mapping.values()) | {f["field_key"] for f in document.get("filters", {}).get("custom_fields", [])}
    if requested - active.keys():
        raise HTTPException(409, "broadcast_segment_field_unavailable")
    if mapping.get("birth_date") and active[mapping["birth_date"]].type != "Date":
        raise HTTPException(422, "broadcast_birth_date_field_required")
    return active


def details(person, document, as_of):
    values = json.loads(person.get("CustomValues", "{}"))
    mapping = document.get("demographic_fields", {})
    age = None
    birth = values.get(mapping.get("birth_date", ""))
    try:
        born = date.fromisoformat(birth) if isinstance(birth, str) else None
        if born and born <= as_of:
            candidate = as_of.year - born.year - ((as_of.month, as_of.day) < (born.month, born.day))
            if 0 <= candidate <= 120:
                age = candidate
    except ValueError:
        pass
    age_band = "Sin dato" if age is None else next(label for limit, label in [(18, "Menos de 18"), (25, "18–24"), (35, "25–34"), (45, "35–44"), (55, "45–54"), (65, "55–64"), (121, "65 o más")] if age < limit)
    result = {
        "gender": gender(values.get(mapping.get("gender", ""), "")),
        "age_band": age_band,
        "city": person.get("City", ""),
        "region": values.get(mapping.get("region", ""), ""),
        "country": values.get(mapping.get("country", ""), ""),
        "program": person.get("Program", ""),
        "schedule": person.get("Schedule", ""),
        "contact_type": person.get("Type", ""),
        "stage": person.get("Stage", ""),
        "last_incoming": RECENCY_LABELS[incoming_bucket(person, document, as_of)],
    }
    return {k: str(v).strip()[:200] if v is not None and str(v).strip() else "Sin dato" for k, v in result.items()}, age, values


def matches(person, document, as_of):
    filters = document.get("filters", {})
    if filters.get("audience_mode") == "contacts" and not filters.get("contact_ids"):
        return False
    bucket = filters.get("last_incoming_bucket", "any")
    if bucket != "any" and incoming_bucket(person, document, as_of) != bucket:
        return False
    profile, age, values = details(person, document, as_of)
    if filters.get("genders") and normalized(profile["gender"]) not in {normalized(gender(v)) for v in filters["genders"]}:
        return False
    if filters.get("age_min") is not None and (age is None or age < filters["age_min"]):
        return False
    if filters.get("age_max") is not None and (age is None or age > filters["age_max"]):
        return False
    for key, filter_key in (("region", "regions"), ("country", "countries")):
        if filters.get(filter_key) and normalized(profile[key]) not in {normalized(v) for v in filters[filter_key]}:
            return False
    for field in filters.get("custom_fields", []):
        value = values.get(field["field_key"])
        allowed = {normalized(v) for v in field["values"]}
        matched = (
            any(v in normalized(value) for v in allowed)
            if field.get("match") == "contains"
            else normalized(value) in allowed
        )
        if value is None or not matched:
            return False
    return True


def snapshot_profile(snapshot):
    profile = json.loads(snapshot or "{}").get("audience_profile", {})
    return {key: str(profile.get(key) or "Sin dato")[:200] for key in DIMENSIONS}


def analytics(items):
    """One bounded pass; historical records without a snapshot stay unknown."""
    grouped = {key: defaultdict(lambda: dict(total=0, delivered=0, read=0, replied=0, failed=0)) for key in DIMENSIONS}
    totals = dict(total=0, delivered=0, read=0, replied=0, failed=0)
    for item in items:
        profile = snapshot_profile(item.get("Snapshot"))
        observed = dict(total=1, delivered=int(bool(item.get("DeliveredAt") or item.get("ReadAt"))), read=int(bool(item.get("ReadAt"))), replied=int(bool(item.get("RepliedAt"))), failed=int(item.get("Status") == "failed"))
        for metric, count in observed.items():
            totals[metric] += count
        for key in DIMENSIONS:
            label = str(profile.get(key) or "Sin dato")[:200]
            bucket = grouped[key][label]
            for metric, count in observed.items():
                bucket[metric] += count
    return {
        "totals": totals,
        "dimensions": {key: [{"label": label, **counts} for label, counts in sorted(groups.items(), key=lambda v: (-v[1]["total"], v[0]))] for key, groups in grouped.items()},
        "data_source": "declared_CRM_at_preparation; absent_historical_snapshots_are_unknown",
        "read_semantics": "WhatsApp_read_receipt; no_separate_open_event",
    }
