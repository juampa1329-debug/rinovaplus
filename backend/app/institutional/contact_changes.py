"""Three-way CRM edits: only the operator's changed fields, under writer lock."""

from fastapi import HTTPException

from app.sql_workspace import Contact

PROTECTED = {"id", "programId", "program", "institutionalProfile"}


def merge_contact_edit(current, requested, base):
    """Unrelated activity is harmless; concurrent edits to the same value conflict.

    The base is supplied by the editor, never an authority/permission. The caller
    still verifies canonical identity, CRM permission, current configuration and
    academic mapping. No guessed academic state or consent is accepted here.
    """
    before, after = base.model_dump(), requested.model_dump()
    actual = Contact.model_validate(current).model_dump()
    if before["id"] != actual["id"] or after["id"] != actual["id"]:
        raise HTTPException(409, "canonical_contact_required")
    if any(before[key] != after[key] for key in PROTECTED):
        raise HTTPException(422, "academic_mapping_not_bound")
    merged = dict(actual)
    for key in after.keys() - PROTECTED - {"customValues"}:
        if before[key] == after[key]:
            continue
        if actual[key] not in (before[key], after[key]):
            raise HTTPException(409, "contact_fields_changed")
        merged[key] = after[key]
    custom = dict(actual["customValues"])
    for key in before["customValues"].keys() | after["customValues"].keys():
        old, new = before["customValues"].get(key), after["customValues"].get(key)
        if old == new:
            continue
        if actual["customValues"].get(key) not in (old, new):
            raise HTTPException(409, "contact_fields_changed")
        if new is None:
            custom.pop(key, None)
        else:
            custom[key] = new
    merged["customValues"] = custom
    return Contact.model_validate(merged)
