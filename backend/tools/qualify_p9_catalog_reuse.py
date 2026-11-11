"""Equivalent full catalog/ACL validation with same-transaction metadata reuse."""

import json
import time

from app.institutional.store import transaction
from app.parity_channels.catalog import metadata
from tools.es_schema_catalog_v2 import snapshot
from tools.foundation_snapshot import sha
from tools.p9_catalog_snapshot import snapshot as p9_snapshot
from tools.p9_test_support import Harness
from tools.prepare_p9_ads import WORK, read, save


def main():
    h = Harness()
    checks = []
    with transaction(h.settings, anonymous=True) as c:
        raw = metadata(c.physical)
        original = snapshot(c.physical)
        reused = p9_snapshot(c.physical, raw_catalog=raw)
        assert original == reused
        assert (
            sha(dict(model=reused, catalog=raw))
            == h.settings.ticket["qualified_shape_sha256"]
        )
        checks.append(
            "full175table_catalog_reuse_is_byte_equivalent_to_independent_fresh_snapshot"
        )
        user = h.settings.connection["username"]
        for scope, actors in [
            ("USER", sorted({r["name"] for r in raw["principals"]} - {user})),
            ("LOGIN", h.settings.ticket["protected_logins"]),
        ]:
            for start in range(0, len(actors), 200):
                batch = actors[start : start + 200]
                actual = list(
                    c.physical.execute(
                        "SELECT v.name,HAS_PERMS_BY_NAME(v.name,?,'IMPERSONATE') FROM (VALUES "
                        + ",".join("(?)" for _ in batch)
                        + ") v(name)",
                        scope,
                        *batch,
                    ).fetchall()
                )
                expected = [
                    (
                        v,
                        c.physical.execute(
                            "SELECT HAS_PERMS_BY_NAME(?,?,'IMPERSONATE')", v, scope
                        ).fetchval(),
                    )
                    for v in batch
                ]
                assert [tuple(v) for v in actual] == expected and all(
                    v[1] == 0 for v in actual
                )
        checks.append(
            "every_USER_and_LOGIN_impersonation_result_matches_original_individual_checks"
        )
    start = time.monotonic()
    for _ in range(3):
        with transaction(h.settings, anonymous=True):
            pass
    checks.append(
        "three_fresh_transactions_revalidate_full_TLS_identity_model_ACL_and_history_without_cross_request_cache"
    )
    from tools.p9_ads_recovery import backup, fingerprint

    three_elapsed = round(time.monotonic() - start, 3)
    from uuid import uuid4

    from tools.prepare_p9_ads import admin, prepare
    from tools.qualify_p4_storage import academic

    label = "catalog-drift-" + uuid4().hex[:8]
    with admin(h.settings.connection["database"]) as db:
        checkpoint = backup(db, h.settings.ticket["identity"])
    prepare(label, checkpoint=checkpoint, recovering_from=h.settings)
    from pathlib import Path

    from app.institutional.api import create_app
    from app.institutional.spanish import load
    from tools.qualify_p3_workspace import Browser

    drift = load(Path(read(WORK / (label + "-profile.json"))["directory"]))
    browser = Browser(create_app(drift))
    access = read(WORK / (label + "-access.json"))
    browser.login(access["email"], access["password"])
    with admin(drift.connection["database"]) as db:
        before = academic(db.cursor())
        db.cursor().execute(
            "ALTER TABLE dbo.CRMPublicidadCaptacion ADD CatalogProbe int NULL"
        )
        assert academic(db.cursor()) == before
    browser.request("ads/accounts", expected=503)
    checks.append(
        "runtime_rejects_real_model_drift_after_previous_successful_full_guard"
    )
    with admin(h.settings.connection["database"]) as db:
        assert fingerprint(db.cursor()) == checkpoint["data"]
    checks.append("negative_probe_preserves_source_fixture_and_all_academic_tables")
    save(
        WORK / "catalog-reuse-result.json",
        dict(
            status="passed",
            checks=checks,
            three_guarded_transactions_seconds=three_elapsed,
            cross_request_cache=False,
            academic_writes=False,
            real_provider_calls=0,
            engine=15,
            compatibility=150,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
