"""Private SIIE drafts/receipts on the existing institutional settings store.

Only bounded receipt metadata is searchable. Form fields are authenticated,
encrypted values; they never become settings history, AI knowledge or logs.
"""

import base64
import json
from uuid import UUID

from app.institutional.crypto import canonical, seal, unseal
from app.institutional.db import institution, key, one


def section(kind, identity):
    if kind not in {"sd", "sw", "se", "sl", "sg", "sf", "sx"}:
        raise ValueError("invalid_siie_record_kind")
    return kind + ":" + UUID(str(identity)).hex


def get(c, settings, kind, identity):
    name = section(kind, identity)
    row = one(
        c,
        "SELECT Document,Revision FROM crm_access.Setting WHERE InstitutionId=? AND Section=?",
        institution(settings),
        name,
    )
    if not row:
        return None
    value = json.loads(row["Document"])
    owner = {"institution": institution(settings), "section": name, "version": 1}
    private = json.loads(
        unseal(
            key(settings),
            owner,
            base64.b64decode(value["nonce"]),
            base64.b64decode(value["ciphertext"]),
        )
    )
    return {
        "revision": row["Revision"],
        "metadata": value["metadata"],
        "private": private,
    }


def put(c, settings, kind, identity, metadata, private, previous=None):
    name = section(kind, identity)
    owner = {"institution": institution(settings), "section": name, "version": 1}
    nonce, encrypted = seal(key(settings), owner, canonical(private).decode())
    value = canonical(
        {
            "metadata": metadata,
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(encrypted).decode(),
        }
    ).decode()
    if previous is None:
        c.execute(
            "INSERT crm_access.Setting(InstitutionId,Section,Document,Revision,UpdatedAt) VALUES(?,?,?,1,SYSUTCDATETIME())",
            institution(settings),
            name,
            value,
        )
        return 1
    c.execute(
        "UPDATE crm_access.Setting SET Document=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND Section=? AND Revision=?",
        value,
        institution(settings),
        name,
        previous["revision"],
    )
    if c.rowcount != 1:
        from fastapi import HTTPException

        raise HTTPException(409, "revision_conflict")
    return previous["revision"] + 1


def recent(c, settings, kind, *, offset=0):
    # Section is <=40 bytes in the installed schema; prefix is not user input.
    if kind not in {"sd", "sw", "se", "sf"}:
        raise ValueError("invalid_siie_record_kind")
    from app.institutional.db import rows, utc

    values = rows(
        c,
        "SELECT Section,Document,Revision,UpdatedAt FROM crm_access.Setting WHERE InstitutionId=? AND Section LIKE ? ORDER BY UpdatedAt DESC,Section OFFSET ? ROWS FETCH NEXT 26 ROWS ONLY",
        institution(settings),
        kind + ":%",
        offset,
    )
    return {
        "items": [
            {
                "id": str(UUID(v["Section"][3:])),
                "revision": v["Revision"],
                "updated_at": utc(v["UpdatedAt"]),
                **json.loads(v["Document"])["metadata"],
            }
            for v in values[:25]
        ],
        "has_more": len(values) > 25,
    }
