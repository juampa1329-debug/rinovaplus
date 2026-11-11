"""Offline history/current-source checks; never load CRM, credentials or ODBC."""

import argparse
import hashlib
import importlib.util
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/adaptation/sql"
C4_BASELINE = DOCS / "sql_c4_input_baseline.json"
C4_PROOF = DOCS / "sql_c4_validation.json"
C5_BASELINE = DOCS / "sql_c5_input_baseline.json"
C5_PROOF = DOCS / "sql_c5_validation.json"
C7_BASELINE = DOCS / "sql_c7_input_baseline.json"
C7_PROOF = DOCS / "sql_c7_validation.json"
C6_PROOF_SHA256 = "0473f6ada7cfae1583d9bac8e210a575c5e410f5c51fdb814f32b297ad54ca0d"
CHANNEL_RELEASES = {
    "cbn_channels": "e4f76c63592b4a99f35380496d25a34afb205645a0c4f5e885cf9ece8f901ca1",
    "cbn_channels_v2": (
        "49f72eb835ce46b83ec9c6267da2f73c9d7799990de6fab8ed28762565985998"
    ),
}
PACKAGE = ROOT / "backend/migrations/cbn_foundation"
RELEASE_SHA256 = "b8de5466cd6c0e8b373490cc0987bacbf90deff95ffe45e8d84f54f6dc08827a"
SOURCE_SUFFIXES = {".py", ".sql", ".json", ".ts", ".tsx", ".css"}
SOURCE_ROOTS = (
    "backend/app",
    "backend/tools",
    "backend/tests",
    "backend/migrations",
    "frontend/src",
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def immutable(path):
    return later_frozen(path) or (
        path.startswith(("backend/migrations/", "../saas-version/"))
        or path.startswith("backend/tools/migrate_")
        or path
        in {
            "backend/tools/cbn_foundation.py",
            "backend/tools/foundation_snapshot.py",
            "backend/tools/foundation_contract.py",
            "docs/adaptation/sql/inventory.json",
            "docs/adaptation/sql/migration-plan.json",
            "docs/adaptation/sql/observed-schema.json",
            "docs/adaptation/sql/horariosiie-comparison.json",
            "docs/adaptation/sql/sql_c2_input_baseline.json",
            "docs/adaptation/sql/sql_c3_input_baseline.json",
            "docs/adaptation/sql/sql_c2_preflight.json",
            "docs/adaptation/sql/sql_c2_destination_metadata.json",
            "docs/adaptation/sql/sql_c2_validation.json",
            "docs/adaptation/sql/sql_c3_validation.json",
            "docs/adaptation/sql/sql_c4_input_baseline.json",
            "docs/adaptation/sql/sql_c4_validation.json",
            "docs/adaptation/sql/sql_c5_input_baseline.json",
            "docs/adaptation/sql/sql_c5_validation.json",
            "docs/adaptation/sql/sql_c6_input_baseline.json",
            "docs/adaptation/sql/sql_c6_validation.json",
            "docs/adaptation/sql/check_c6_plan.py",
            "docs/adaptation/sql/crm-extension-plan.json",
            "docs/adaptation/fragments/sql-c6.json",
            "docs/adaptation/sql/SQL_C6_REVIEW.md",
            "docs/adaptation/sql/sql_c7_input_baseline.json",
            "backend/tools/crm_extension.py",
            "backend/tools/crm_extension_snapshot.py",
            "backend/tools/crm_extension_contract.py",
            "backend/tools/crm_extension_v2.py",
            "backend/tools/crm_extension_snapshot_v2.py",
        }
    )


def channel_assets():
    """Exact additive C7 assets; existing migrations never become mutable."""
    files = {}
    for package, expected in CHANNEL_RELEASES.items():
        path = ROOT / "backend/migrations" / package / "release.json"
        if digest(path) != expected:
            raise ValueError("C7 frozen release changed: " + package)
        files[path.relative_to(ROOT).as_posix()] = expected
        for record in read(path)["files"]:
            if digest(ROOT / record["path"]) != record["sha256"]:
                raise ValueError("C7 frozen asset changed: " + record["path"])
            files[record["path"]] = record["sha256"]
    return verify_c11_assets(verify_previous_assets(files))


def verify_c6_history():
    """Run the unchanged C6 checker against authenticated public preimages."""
    proof_path = DOCS / "sql_c6_validation.json"
    if digest(proof_path) != C6_PROOF_SHA256:
        raise ValueError("C6 historical proof changed")
    proof = read(proof_path)
    checker = DOCS / "check_c6_plan.py"
    for path, expected in (
        (checker, proof["checker_sha256"]),
        (DOCS / "crm-extension-plan.json", proof["plan_sha256"]),
        (DOCS / "sql_c6_input_baseline.json", proof["baseline_sha256"]),
    ):
        if digest(path) != expected:
            raise ValueError("C6 design artifact changed: " + path.name)
    archive = proof["public_input_preimages"]
    if digest(ROOT / archive["path"]) != archive["sha256"]:
        raise ValueError("C6 public preimages changed or missing")
    baseline = read(DOCS / "sql_c6_input_baseline.json")
    images = {}
    with zipfile.ZipFile(ROOT / archive["path"]) as source:
        if source.testzip() is not None or len(source.namelist()) != archive["files"]:
            raise ValueError("C6 preimage CRC or membership changed")
        for record in baseline["files"]:
            path = record["path"]
            member = (
                "reference/" + path[3:]
                if path.startswith("../")
                else "target/CRM_CBN/" + path
            )
            content = source.read(member)
            if hashlib.sha256(content).hexdigest() != record["sha256"]:
                raise ValueError("C6 preimage changed: " + path)
            images[(ROOT / path).resolve()] = content
    spec = importlib.util.spec_from_file_location("c6_historical_design", checker)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def historical_bytes(path):
        return images[path.resolve()] if path.resolve() in images else path.read_bytes()

    module.digest = lambda path: hashlib.sha256(historical_bytes(path)).hexdigest()
    module.read = lambda path: json.loads(historical_bytes(path).decode("utf-8-sig"))
    plan = module.read(DOCS / "crm-extension-plan.json")
    count = module.validate(plan)
    negatives = module.self_test(plan)
    if count != proof["protected_inputs"] or negatives != proof["negative_checks"]:
        raise ValueError("C6 historical design no longer reproduces")
    return {"inputs": count, "negative_checks": len(negatives)}


def verify_frozen_release():
    release_path = PACKAGE / "release.json"
    if digest(release_path) != RELEASE_SHA256:
        raise ValueError(
            "Frozen C3 release changed; later checkpoints cannot replace it"
        )
    release = read(release_path)
    records = [*release["tool_files"], *release["legacy_sources"]]
    records += [
        {
            "path": "backend/migrations/cbn_foundation/" + u["file"],
            "sha256": u["sha256"],
        }
        for u in release["units"]
    ]
    records.append(
        {
            "path": "backend/migrations/cbn_foundation/expected-shapes.json",
            "sha256": release["expected_shapes_sha256"],
        }
    )
    for record in records:
        if digest(ROOT / record["path"]) != record["sha256"]:
            raise ValueError("Frozen C3 input changed: " + record["path"])
    return RELEASE_SHA256


def stage_changes(stage, baseline, proof, proof_path):
    """Validate a stage's preimages without substituting the current filesystem."""
    changes = {}
    for record in proof["changed_files"]:
        path = record["path"]
        if (
            not isinstance(path, str)
            or Path(path).is_absolute()
            or "\\" in path
            or ":" in path
            or any(p in {"", ".", ".."} for p in path.split("/"))
            or any(
                p in {".env", ".local", ".git", "__pycache__", "node_modules"}
                for p in path.split("/")
            )
        ):
            raise ValueError("Invalid " + stage + " change path")
        if (
            path in changes or stage_forbidden_change(stage, path)
            or (
                immutable(path)
                and not (
                    stage in ADDITIVE_STAGES
                    and record["before_sha256"] is None
                    and channel_assets().get(path) == record["after_sha256"]
                )
            )
            or path == proof_path.relative_to(ROOT).as_posix()
        ):
            raise ValueError(
                "Repeated, frozen or self-referential " + stage + " change: " + path
            )
        before, after = record["before_sha256"], record["after_sha256"]
        if any(
            v is not None
            and (not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v))
            for v in (before, after)
        ):
            raise ValueError("Invalid " + stage + " change hash: " + path)
        if before != baseline.get(path) or before == after:
            raise ValueError(
                stage + " preimage is absent, changed or not a change: " + path
            )
        changes[path] = record
    return changes


def previous_checkpoint(previous_sha256, baseline, proof=None):
    records = {r["path"]: r["sha256"] for r in baseline["files"]}
    if (
        not previous_sha256
        or baseline.get("unit") != "SQL-C5"
        or baseline.get("previous_checkpoint_sha256") != previous_sha256
        or records.get("docs/adaptation/sql/sql_c4_validation.json") != previous_sha256
        or (
            proof is not None
            and proof.get("previous_checkpoint_sha256") != previous_sha256
        )
    ):
        raise ValueError("SQL-C5 previous C4 checkpoint is missing or changed")


def validate_proof(stage, status, proof, baseline_sha256):
    if proof.get("stage") != stage or proof.get("status") != status:
        raise ValueError(stage + " evidence is not an accepted checkpoint")
    if not baseline_sha256 or proof.get("input_baseline_sha256") != baseline_sha256:
        raise ValueError(stage + " input baseline hash is missing or changed")


def checkpoint_chain():
    checkpoints = []
    for stage, baseline_path, proof_path, status in (
        ("SQL-C4", C4_BASELINE, C4_PROOF, "accepted_restored_repositories_only"),
        ("SQL-C5", C5_BASELINE, C5_PROOF, "accepted_restored_ui_only"),
        ("SQL-C7", C7_BASELINE, C7_PROOF, "accepted_restored_channels_only"),
        (
            "SQL-C8",
            C8_BASELINE,
            C8_PROOF,
            "accepted_restored_channels_repositories_only",
        ),
    ):
        if stage == "SQL-C5" and baseline_path.is_file():
            baseline_document = read(baseline_path)
            previous_checkpoint(digest(C4_PROOF), baseline_document)
        if not proof_path.is_file():
            if stage == "SQL-C4" and C5_PROOF.is_file():
                raise ValueError("SQL-C5 requires the accepted SQL-C4 checkpoint")
            continue
        proof = read(proof_path)
        validate_proof(stage, status, proof, digest(baseline_path))
        baseline_document = read(baseline_path)
        baseline = {r["path"]: r["sha256"] for r in baseline_document["files"]}
        if stage == "SQL-C5":
            previous_checkpoint(digest(C4_PROOF), baseline_document, proof)
            for path, change in checkpoints[0]["changes"].items():
                if baseline.get(path) != change["after_sha256"]:
                    raise ValueError(
                        "SQL-C5 baseline does not preserve the C4 postimage: " + path
                    )
        if stage == "SQL-C7":
            previous = digest(C5_PROOF)
            if (
                baseline_document.get("unit") != stage
                or baseline_document.get("previous_checkpoint_sha256") != previous
                or proof.get("previous_checkpoint_sha256") != previous
                or baseline.get("docs/adaptation/sql/sql_c5_validation.json")
                != previous
                or baseline_document.get("design_checkpoint_sha256") != C6_PROOF_SHA256
                or proof.get("design_checkpoint_sha256") != C6_PROOF_SHA256
            ):
                raise ValueError("C7 parent C5 or design C6 changed")
            preserve_latest_baseline(
                baseline, checkpoints, proof.get("inherited_postimages", {})
            )
            channel_assets()
            verify_c6_history()
        if stage == "SQL-C8":
            validate_c8_parent(baseline_document, proof)
            graph_inputs = verify_c8_graph_inputs(proof)
            if set(graph_inputs) & set(baseline):
                raise ValueError("C8 graph supplement must not replace baseline inputs")
            baseline = baseline | graph_inputs
            preserve_latest_baseline(
                baseline, checkpoints, proof.get("inherited_postimages", {})
            )
            verify_c7_additions({})
        checkpoints.append(
            {
                "stage": stage,
                "status": status,
                "baseline_path": baseline_path,
                "proof_path": proof_path,
                "baseline": baseline_document,
                "changes": stage_changes(stage, baseline, proof, proof_path),
            }
        )
    return all_later_checkpoints(checkpoints)


def chain_changes(checkpoints):
    changes = {}
    for checkpoint in checkpoints:
        for path, record in checkpoint["changes"].items():
            history = changes.setdefault(path, [])
            if history and history[-1]["after_sha256"] != record["before_sha256"]:
                raise ValueError("Broken checkpoint transition chain: " + path)
            history.append(record)
    return changes


def preserve_latest_baseline(baseline, checkpoints, inherited=None):
    latest = {
        path: history[-1]["after_sha256"]
        for path, history in chain_changes(checkpoints).items()
    }
    missing = {
        path: value
        for path, value in latest.items()
        if path not in baseline and value is not None
    }
    if (inherited or {}) != missing:
        raise ValueError("C7 inherited postimages are incomplete or changed")
    combined = {**(inherited or {}), **baseline}
    for path, value in latest.items():
        if combined.get(path) != value:
            raise ValueError("C7 baseline lost latest previous postimage: " + path)


def approved_changes():
    return chain_changes(checkpoint_chain())


def checkpoint_evidence_files():
    return [
        p for c in checkpoint_chain() for p in (c["baseline_path"], c["proof_path"])
    ]


def checkpoint_statuses():
    return {c["stage"]: c["status"] for c in checkpoint_chain()}


def changed_source_paths():
    return [
        ROOT / path
        for path, history in approved_changes().items()
        if history[-1]["after_sha256"] is not None
    ]


def verify_record(path, expected, current, changes):
    if current == expected:
        return False
    history = changes.get(path, [])
    if isinstance(history, dict):
        history = [history]
    value, recognized = expected, False
    for change in history:
        if change["before_sha256"] == value:
            value, recognized = change["after_sha256"], True
    additive_c7 = (
        (
            expected is None
            and len(history) == 1
            and history[0]["before_sha256"] is None
            and path in channel_assets()
        )
        if immutable(path) and C7_PROOF.is_file()
        else False
    )
    if (immutable(path) and not additive_c7) or not recognized or value != current:
        raise ValueError("Unapproved change from historical checkpoint: " + path)
    return True


def verify_records(records, changes=None):
    changes = approved_changes() if changes is None else changes
    recognized = 0
    for record in records:
        path = record.get("path", record.get("file"))
        recognized += verify_record(
            path, record["sha256"], digest(ROOT / path), changes
        )
    return recognized


def verify_historical_manifest(path, field="inputs"):
    """Rebuilding a graph must not silently refresh its immutable input hashes."""
    if path.is_file():
        records = [
            r for r in read(path)[field] if immutable(r.get("path", r.get("file")))
        ]
        verify_records(records, {})


def current_source_paths(stage):
    current = {
        p.relative_to(ROOT).as_posix()
        for directory in SOURCE_ROOTS
        for p in (ROOT / directory).rglob("*")
        if p.is_file()
        and p.suffix in SOURCE_SUFFIXES
        and "__pycache__" not in p.parts
        and "graphify-out" not in p.parts
    }
    if stage in COMPOSE_STAGES:
        current.update(
            p.relative_to(ROOT).as_posix()
            for pattern in ("compose*.yaml", "compose*.yml")
            for p in ROOT.glob(pattern)
            if p.is_file()
        )
    return current


def verify_active_checkpoint():
    """Validate C4→C5→C7 history and every current source addition/deletion."""
    verify_frozen_release()
    checkpoints = checkpoint_chain()
    changes = chain_changes(checkpoints)
    if not checkpoints:
        return False
    for checkpoint in checkpoints:
        verify_records(checkpoint["baseline"]["files"], changes)
    records = checkpoints[-1]["baseline"]["files"]
    original = {r["path"] for r in records}
    current = current_source_paths(checkpoints[-1]["stage"])
    for path in current - original:
        verify_record(path, None, digest(ROOT / path), changes)
    for path, history in changes.items():
        verify_record(path, history[0]["before_sha256"], digest(ROOT / path), changes)
    return True


def self_test():
    old, new = "a" * 64, "b" * 64
    path = "backend/app/example.py"
    changes = {path: {"before_sha256": old, "after_sha256": new}}
    assert not verify_record(path, old, old, {})
    assert verify_record(path, old, new, changes)
    for candidate, expected, actual, permitted in (
        (path, old, new, {}),
        (path, "c" * 64, new, changes),
        (path, old, "c" * 64, changes),
        (
            "backend/tools/foundation_snapshot.py",
            old,
            new,
            {"backend/tools/foundation_snapshot.py": changes[path]},
        ),
    ):
        try:
            verify_record(candidate, expected, actual, permitted)
        except ValueError:
            pass
        else:
            raise AssertionError("Unapproved/frozen change was accepted")
    middle = "c" * 64
    first = {"before_sha256": old, "after_sha256": middle}
    second = {"before_sha256": middle, "after_sha256": new}
    chain = chain_changes([{"changes": {path: first}}, {"changes": {path: second}}])
    assert verify_record(path, old, new, chain)
    assert verify_record(path, middle, new, chain)
    stages = [{"changes": {path: first}}, {"changes": {path: second}}]
    preserve_latest_baseline({path: new}, stages)
    try:
        preserve_latest_baseline({path: middle}, stages)
    except ValueError:
        pass
    else:
        raise AssertionError("An older intermediate postimage was accepted")
    preserve_latest_baseline({}, stages, {path: new})
    for inherited in ({}, {path: middle}, {path: new, "extra": new}):
        try:
            preserve_latest_baseline({}, stages, inherited)
        except ValueError:
            pass
        else:
            raise AssertionError("Missing or changed inherited pins were accepted")
    creation = {"before_sha256": None, "after_sha256": old}
    assert verify_record(path, None, old, {path: [creation]})
    assert verify_record(
        path, old, None, {path: [{"before_sha256": old, "after_sha256": None}]}
    )
    c4_path = "docs/adaptation/sql/sql_c4_validation.json"
    baseline = {
        "unit": "SQL-C5",
        "previous_checkpoint_sha256": old,
        "files": [{"path": c4_path, "sha256": old}],
    }
    previous_checkpoint(old, baseline, {"previous_checkpoint_sha256": old})
    proof = {
        "stage": "SQL-C5",
        "status": "accepted_restored_ui_only",
        "input_baseline_sha256": old,
    }
    validate_proof("SQL-C5", "accepted_restored_ui_only", proof, old)
    status = "accepted_restored_ui_only"
    rejected = [
        (verify_record, (path, old, new, {path: [second]})),
        (verify_record, (path, old, new, {path: [first]})),
        (verify_record, (path, None, new, {})),
        (verify_record, (path, old, None, {})),
        (
            verify_record,
            (
                c4_path,
                old,
                new,
                {c4_path: [{"before_sha256": old, "after_sha256": new}]},
            ),
        ),
        (
            chain_changes,
            (
                [
                    {"changes": {path: first}},
                    {"changes": {path: {"before_sha256": new, "after_sha256": old}}},
                ],
            ),
        ),
        (previous_checkpoint, (new, baseline)),
        (previous_checkpoint, (old, baseline, {"previous_checkpoint_sha256": new})),
        (previous_checkpoint, (old, {**baseline, "files": []})),
        (validate_proof, ("SQL-C5", status, {**proof, "stage": "SQL-C4"}, old)),
        (validate_proof, ("SQL-C5", status, {**proof, "status": "pending"}, old)),
        (validate_proof, ("SQL-C5", status, proof, new)),
        (validate_proof, ("SQL-C5", status, proof, None)),
        (
            stage_changes,
            (
                "SQL-C5",
                {path: old},
                {
                    "changed_files": [
                        {"path": path, "before_sha256": middle, "after_sha256": new}
                    ]
                },
                C5_PROOF,
            ),
        ),
        (
            stage_changes,
            (
                "SQL-C5",
                {c4_path: old},
                {
                    "changed_files": [
                        {"path": c4_path, "before_sha256": old, "after_sha256": new}
                    ]
                },
                C5_PROOF,
            ),
        ),
    ]
    for function, arguments in rejected:
        try:
            function(*arguments)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid C4->C5 transition was accepted")
    if C7_PROOF.is_file():
        new_path = "backend/tools/crm_extension_v2.py"
        after = channel_assets()[new_path]
        change = {"path": new_path, "before_sha256": None, "after_sha256": after}
        assert stage_changes("SQL-C7", {}, {"changed_files": [change]}, C7_PROOF)
        assert verify_record(new_path, None, after, {new_path: [change]})
        for invalid in (
            {**change, "before_sha256": old},
            {**change, "after_sha256": old},
            {**change, "path": "backend/migrations/999_unreviewed.sql"},
        ):
            try:
                stage_changes("SQL-C7", {}, {"changed_files": [invalid]}, C7_PROOF)
            except ValueError:
                pass
            else:
                raise AssertionError("C7 admitted a frozen edit or unpinned addition")
        print("C7 additive release checks passed; 3 unsafe transitions rejected")
    print("Offline chain checks passed; 23 invalid transitions rejected")
    c8_baseline = {
        "unit": "SQL-C8",
        "previous_checkpoint_sha256": C7_PROOF_SHA256,
        "files": [
            {
                "path": "docs/adaptation/sql/sql_c7_validation.json",
                "sha256": C7_PROOF_SHA256,
            }
        ],
    }
    c8_proof = {"stage": "SQL-C8", "previous_checkpoint_sha256": C7_PROOF_SHA256}
    validate_c8_parent(c8_baseline, c8_proof)
    for candidate, candidate_proof in (
        ({**c8_baseline, "unit": "SQL-C7"}, c8_proof),
        ({**c8_baseline, "previous_checkpoint_sha256": old}, c8_proof),
        ({**c8_baseline, "files": []}, c8_proof),
        (c8_baseline, {**c8_proof, "previous_checkpoint_sha256": old}),
        (c8_baseline, {**c8_proof, "stage": "SQL-C7"}),
    ):
        try:
            validate_c8_parent(candidate, candidate_proof)
        except ValueError:
            pass
        else:
            raise AssertionError("C8 accepted a changed or missing parent")
    for path, before, after in (
        (
            "docs/adaptation/sql/SQL_C7_REVIEW.md",
            FROZEN_C7_ADDITIONS["docs/adaptation/sql/SQL_C7_REVIEW.md"],
            old,
        ),
        ("backend/migrations/999_unapproved.sql", None, old),
    ):
        try:
            stage_changes(
                "SQL-C8",
                {path: before},
                {
                    "changed_files": [
                        {"path": path, "before_sha256": before, "after_sha256": after}
                    ]
                },
                C8_PROOF,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("C8 accepted frozen evidence edits or new SQL")
    print("C8 history checks passed; 7 unsafe transitions rejected")
    for candidate in ({}, {"graph_input_baseline_sha256": "a" * 64}):
        try:
            verify_c8_graph_inputs(candidate)
        except ValueError:
            pass
        else:
            raise AssertionError("C8 graph supplement accepted an invalid pin")
    print("C8 graph checks passed; 2 invalid pins rejected")


# New checkpoint constants are below the historical definitions to retain the
# frozen C7 fragment's source anchors. No historical evidence is rewritten.
C8_BASELINE = DOCS / "sql_c8_input_baseline.json"
C8_PROOF = DOCS / "sql_c8_validation.json"
C7_PROOF_SHA256 = "0ab917e62830a54461f51659ca448cc75f2b0e56a79098de674f107a1e3c96e2"
FROZEN_C7_ADDITIONS = {
    "docs/adaptation/sql/SQL_C7_REVIEW.md": (
        "f1bf30494f1a28bda9f711e9705b539a1b2a6ecb772ea31c7af6f5dbcb73358c"
    ),
    "docs/adaptation/sql/sql_c7_v1_retirement.json": (
        "82575e97e538e99543abfb771385ccd70835e7041fe9ac3de406aeecf6c1769e"
    ),
    "docs/adaptation/fragments/sql-c7.json": (
        "f4387b8013254aa13ebc2b30b807c49ddfae829c15179ce0f63525594de04619"
    ),
    "docs/decisions/ADR-019-channels-restored-extension.md": (
        "3ca081fdc1d58ac811da0a80e3e40176f48ea1f5854dd79f97c4354b9c09860d"
    ),
}
C8_FROZEN = {
    "docs/adaptation/sql/sql_c7_validation.json",
    "docs/adaptation/sql/sql_c8_input_baseline.json",
    "docs/adaptation/sql/sql_c8_graph_input_baseline.json",
    *FROZEN_C7_ADDITIONS,
}


def verify_c7_additions(files):
    if digest(C7_PROOF) != C7_PROOF_SHA256:
        raise ValueError("Frozen C7 proof changed")
    for path, expected in FROZEN_C7_ADDITIONS.items():
        if digest(ROOT / path) != expected:
            raise ValueError("Frozen C7 evidence changed: " + path)
    return files | FROZEN_C7_ADDITIONS


def validate_c8_parent(baseline, proof):
    parents = {r["path"]: r["sha256"] for r in baseline["files"]}
    if (
        baseline.get("unit") != "SQL-C8"
        or proof.get("stage") != "SQL-C8"
        or baseline.get("previous_checkpoint_sha256") != C7_PROOF_SHA256
        or proof.get("previous_checkpoint_sha256") != C7_PROOF_SHA256
        or digest(C7_PROOF) != C7_PROOF_SHA256
        or parents.get("docs/adaptation/sql/sql_c7_validation.json") != C7_PROOF_SHA256
    ):
        raise ValueError("C8 parent C7 is missing or changed")


def verify_c8_graph_inputs(proof):
    """Authenticate only the four living parity fragments before anchor refresh."""
    path = DOCS / "sql_c8_graph_input_baseline.json"
    if digest(path) != proof.get("graph_input_baseline_sha256"):
        raise ValueError("C8 graph supplement is absent or changed")
    baseline = read(path)
    allowed = {
        "docs/adaptation/fragments/" + name + ".json"
        for name in ("ai-memory", "foundation", "inbox-crm", "marketing")
    }
    entries = {r["path"]: r["sha256"] for r in baseline["files"]}
    if (
        baseline.get("unit") != "SQL-C8-anchor-refresh"
        or set(entries) != allowed
        or len(baseline["files"]) != len(allowed)
    ):
        raise ValueError("C8 graph supplement membership changed")
    archive = baseline["archive"]
    if digest(ROOT / archive["path"]) != archive["sha256"]:
        raise ValueError("C8 graph preimages changed or missing")
    with zipfile.ZipFile(ROOT / archive["path"]) as source:
        if (
            set(source.namelist()) != allowed | {"source-manifest.json"}
            or source.testzip()
        ):
            raise ValueError("C8 graph preimage membership/CRC changed")
        manifest = source.read("source-manifest.json")
        if hashlib.sha256(manifest).hexdigest() != baseline["parent_manifest_sha256"]:
            raise ValueError("C8 previous graph manifest changed")
        prior = {r["path"]: r["sha256"] for r in json.loads(manifest)["files"]}
        for name, expected in entries.items():
            if (
                prior.get(name) != expected
                or hashlib.sha256(source.read(name)).hexdigest() != expected
            ):
                raise ValueError("C8 graph source preimage changed: " + name)
    return entries


# C9 is appended below closed C8 definitions to preserve native graph anchors.
C9_BASELINE = DOCS / "sql_c9_input_baseline.json"
C9_PROOF = DOCS / "sql_c9_validation.json"
C8_PROOF_SHA256 = "ae2cc30af2adfb39d1948fb0f3648d785db205374305e80b5425f2d299997e19"
FROZEN_C8_ADDITIONS = {
    "backend/app/channels_app.py": (
        "004756ca8f0850b6eafa44452dfe20f74f58d7730267bbeb8a5a8dcc81d46194"
    ),
    "backend/app/channels_catalog.py": (
        "a335113e72a9c007d6c895d2898df05f645b40fe305418ddefe7e0f42d8f668b"
    ),
    "backend/app/channels_contract.py": (
        "23717718db287e30a44456b7465451d7b2fa60144d0464abf0890b5c28b4ebeb"
    ),
    "backend/app/channels_profile.py": (
        "0c2399c4fd45cb8b7e6cc4469019d0cb9073310fda7b01a1b3444d6c51efd4f5"
    ),
    "backend/tools/rehearse_channels.py": (
        "560df6e1937a6d57623d0619aebe88ca6e76e28581fa2960f4eaf73ff4f2ba1f"
    ),
    "backend/tools/check_channels.py": (
        "3d2c77cf44d8e8e3c74499db1b39cac427b6015e9d05140874216873a8b7c4d2"
    ),
    "backend/tests/test_channels_runtime.py": (
        "c9a90d59d2bf210b7fc5ba2a59838ad7b0fd00db5e999a81589bef41964fcefd"
    ),
    "docs/adaptation/sql/SQL_C8_REVIEW.md": (
        "c50b6fa464344a9db7329dc452295e004df37227847818bac33102f9619560f5"
    ),
    "docs/decisions/ADR-020-channels-repository-rehearsal.md": (
        "9589654f98797e6d19d96301145e3d2491c4991f45d33f0da8d1a517b061aa73"
    ),
    "docs/adaptation/fragments/sql-c8.json": (
        "4d19931eb0126413af187ae61baddefd5add73dc7e3210e89b7ec14dc85fee6d"
    ),
    "docs/adaptation/sql/sql_c8_anchor_changes.json": (
        "4fc4905fc8156c7f8dfa1ba54d8be97ab575cf9802dfae0920a87b6470760816"
    ),
}
C9_FROZEN = {
    "docs/adaptation/sql/sql_c8_validation.json",
    "docs/adaptation/sql/sql_c9_input_baseline.json",
    *FROZEN_C8_ADDITIONS,
}


def verify_c8_additions(files):
    if digest(C8_PROOF) != C8_PROOF_SHA256:
        raise ValueError("Frozen C8 proof changed")
    for path, expected in FROZEN_C8_ADDITIONS.items():
        if digest(ROOT / path) != expected:
            raise ValueError("Frozen C8 source or evidence changed: " + path)
    return files | FROZEN_C8_ADDITIONS


def validate_c9_parent(baseline, proof):
    parents = {r["path"]: r["sha256"] for r in baseline["files"]}
    if (
        baseline.get("unit") != "SQL-C9"
        or proof.get("stage") != "SQL-C9"
        or baseline.get("previous_checkpoint_sha256") != C8_PROOF_SHA256
        or proof.get("previous_checkpoint_sha256") != C8_PROOF_SHA256
        or digest(C8_PROOF) != C8_PROOF_SHA256
        or parents.get("docs/adaptation/sql/sql_c8_validation.json") != C8_PROOF_SHA256
    ):
        raise ValueError("C9 parent C8 is missing or changed")


def append_c9_checkpoint(checkpoints):
    if not C9_PROOF.is_file():
        return checkpoints
    baseline_document, proof = read(C9_BASELINE), read(C9_PROOF)
    validate_c9_parent(baseline_document, proof)
    validate_proof(
        "SQL-C9", "accepted_restored_channels_ui_only", proof, digest(C9_BASELINE)
    )
    baseline = {r["path"]: r["sha256"] for r in baseline_document["files"]}
    preserve_latest_baseline(
        baseline, checkpoints, proof.get("inherited_postimages", {})
    )
    verify_c8_additions({})
    checkpoints.append(
        {
            "stage": "SQL-C9",
            "status": proof["status"],
            "baseline_path": C9_BASELINE,
            "proof_path": C9_PROOF,
            "baseline": baseline_document,
            "changes": stage_changes("SQL-C9", baseline, proof, C9_PROOF),
        }
    )
    return checkpoints


def self_test_c9():
    baseline = {
        "unit": "SQL-C9",
        "previous_checkpoint_sha256": C8_PROOF_SHA256,
        "files": [
            {
                "path": "docs/adaptation/sql/sql_c8_validation.json",
                "sha256": C8_PROOF_SHA256,
            }
        ],
    }
    proof = {"stage": "SQL-C9", "previous_checkpoint_sha256": C8_PROOF_SHA256}
    validate_c9_parent(baseline, proof)
    for changed, changed_proof in (
        ({**baseline, "unit": "SQL-C8"}, proof),
        ({**baseline, "previous_checkpoint_sha256": "a" * 64}, proof),
        ({**baseline, "files": []}, proof),
        (baseline, {**proof, "stage": "SQL-C8"}),
        (baseline, {**proof, "previous_checkpoint_sha256": "a" * 64}),
    ):
        try:
            validate_c9_parent(changed, changed_proof)
        except ValueError:
            pass
        else:
            raise AssertionError("C9 accepted a changed or missing parent")
    for path, before in (
        (
            "backend/app/channels_contract.py",
            FROZEN_C8_ADDITIONS["backend/app/channels_contract.py"],
        ),
        (
            "docs/adaptation/fragments/sql-c8.json",
            FROZEN_C8_ADDITIONS["docs/adaptation/fragments/sql-c8.json"],
        ),
        ("backend/migrations/999_unapproved.sql", None),
    ):
        try:
            stage_changes(
                "SQL-C9",
                {path: before},
                {
                    "changed_files": [
                        {
                            "path": path,
                            "before_sha256": before,
                            "after_sha256": "a" * 64,
                        }
                    ]
                },
                C9_PROOF,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("C9 accepted frozen edits or unapproved SQL")
    print("C9 history checks passed; 8 unsafe transitions rejected")


# C10 contract-only checkpoint follows all closed native definitions.
C10_BASELINE = DOCS / "sql_c10_input_baseline.json"
C10_REFERENCES = DOCS / "sql_c10_reference_baseline.json"
C10_PROOF = DOCS / "sql_c10_validation.json"
C9_PROOF_SHA256 = "f7615b5885d7e502aec07030f61ed8bb7a8d0f986d9f99995b46afd0d41a18cb"
FROZEN_C9_ADDITIONS = {
    "artifacts/sql-c9/backend-results.xml": (
        "09a8b9b5e772bb35462c149e7c4be3457533da0fb0557c1b467617adae5caea5"
    ),
    "artifacts/sql-c9/browser-validation.json": (
        "bcb56b7dc9b249c6e192a1cdfce3cb284e663396d1863c8aecba2ddf08046596"
    ),
    "artifacts/sql-c9/connected-checks.json": (
        "f2185cb906ee8741c774cdff099a538b377509ec3afbd00d6710896ff558f2d5"
    ),
    "artifacts/sql-c9/desktop-final.png": (
        "40a2849067a8d345c7395d21d9ad7450cf4313f0183d4d7774f5ffeb37a09198"
    ),
    "artifacts/sql-c9/frontend-results.xml": (
        "01f4f4c4cbf68d30f17e2804fd9d8f644afbbc4431fef151d99dbbf395dd375c"
    ),
    "artifacts/sql-c9/graph-diagnostics.json": (
        "bf504548ebec9da3340cc4281c92c880f537f87309aa47be370e33c4a9ca07ab"
    ),
    "artifacts/sql-c9/http-smoke.json": (
        "3b2868bf30e8918327a9094b8a476fd6c3053632df0ce8bcd3416ded36ccbe37"
    ),
    "artifacts/sql-c9/mobile-conflict.png": (
        "f86082dd0ff2f53beac7dff24ca1ee890abc39670ee3897b82f548938feeb60c"
    ),
    "artifacts/sql-c9/mobile-light.png": (
        "9f1bb385a2ce0073bc2b40c11569bfab8fc03703e97807fe723ac4de38cef78f"
    ),
    "artifacts/sql-c9/mobile-scentra-groups.png": (
        "0084b9319c47571fcdebe3b07a032cd75dbf8f5054a666de5456b0bb3cf4a941"
    ),
    "artifacts/sql-c9/mobile-unavailable.png": (
        "ec3ee0ffceeb886cbd9dcb533d533980649bee5c259cc975184332795413d6a7"
    ),
    "artifacts/sql-c9/preparation.json": (
        "ed7574cac7e641a3c8d173267f6e7d3d29c7a1e24b57fbfedcfc7ae4df49aeb9"
    ),
    "artifacts/sql-c9/preservation-result.json": (
        "919693ea6d8353d375a99cb41d4afdc6e5727fe671f3f9cf0f3d5da30df4bd2f"
    ),
    "backend/app/channels_ui_app.py": (
        "2f0100a1caffb0ad85b5d368299e25887b378579ddca2cdc6f80235e9d19d2bc"
    ),
    "backend/app/channels_ui_contract.py": (
        "80ed32ee43584fed4176126c817a5980c71cd21b542e0b9c5b061ca7a6868311"
    ),
    "backend/app/channels_ui_profile.py": (
        "8a6f6580c35bf6207ae4b28e0f0901abd3b8a60ec6170887e3bdd49a438223a4"
    ),
    "backend/tests/test_channels_ui_runtime.py": (
        "cc4b610890f2cd49ce91d87e5c3d71e658785c0c77fde018785f79e507467d1b"
    ),
    "backend/tools/check_channels_ui.py": (
        "16910ed9398e9ce3802ddd4f0d78cbf94903d46769cce3b9bae7791118842991"
    ),
    "backend/tools/rehearse_channels_ui.py": (
        "53d873112cc2e2eda1031f3ee72695f55a4ee86bcb87b3976cc00342ca26e595"
    ),
    "docs/adaptation/fragments/sql-c9-scentra-parity.json": (
        "6826465347951da75fd2d44fd2e6f03eed9f0854c026ce1b504fd0f67e6d63d3"
    ),
    "docs/adaptation/fragments/sql-c9.json": (
        "5334b1257b58b0b38fd499c2a9e3b90d840452b2fd063ddbf8c3a32ebea94af9"
    ),
    "docs/adaptation/sql/SQL_C9_REVIEW.md": (
        "0d3c9366c1c7e67f057bef62a7ccbbb07ff8e7d9f2024cad51fb5404f59109dc"
    ),
    "docs/adaptation/sql/SQL_C9_SCENTRA_PARITY.md": (
        "a5101c2bc285ea265122057dfead8d688adc616cb266ded2bd664b158b670b40"
    ),
    "docs/decisions/ADR-021-channels-capability-ui.md": (
        "fd8cb48e7b157a2cebd49b600453ea7aa96cdf387c6c22e5c898b6a7706f3bbe"
    ),
    "frontend/src/features/ChannelsUiPanel.tsx": (
        "71e40da8883c9352bf99e794435c31fa87e6d86ecec33f8a753725d37fce851f"
    ),
    "frontend/src/features/ChannelsWorkspace.tsx": (
        "215d4cb6b189d471a303418a81cab7bfdff1a4cae506794757f76f7f5bf0c573"
    ),
    "frontend/src/features/channels-ui.css": (
        "0ddd3dbcd0a212d9945e9d599a00c8db45b5cd8840750a3d1615f380b35696ac"
    ),
    "frontend/src/test/channelsUi.test.tsx": (
        "b536d63b4a07a4e4b40c56fb67abefc46e3e6c63cd0e117ff5b4504d354bbe47"
    ),
    "tasks/sql-c9-progress.json": (
        "533936e5d5f3fbbd1f826b2442adac7de25a75dcaa5b3edfa94155f26ea42c7e"
    ),
    "compose.channels-ui.yaml": (
        "50b8b29f50e5fe02a9dd80e4453a7084dd1925e30acf306d2b32528c29350642"
    ),
    "docker/channels-ui-start.sh": (
        "7c1f5e507ac7514ce261b1dea1e2d67cddf720adeec6636591af34a3db8473f7"
    ),
    "docker/nginx.channels-ui.conf": (
        "bdac433e1dde6f101aeeaba79d9d84f693e8d2f583fe78ca633165ac3f01db15"
    ),
}
C10_FROZEN = {
    "docs/adaptation/sql/sql_c9_validation.json",
    "docs/adaptation/sql/sql_c10_input_baseline.json",
    "docs/adaptation/sql/sql_c10_reference_baseline.json",
    *FROZEN_C9_ADDITIONS,
}


def later_frozen(path):
    return (
        path in C8_FROZEN or path in C9_FROZEN
        or path in C10_FROZEN or path in C11_FROZEN
    )


def c10_forbidden_change(stage, path):
    return stage == "SQL-C10" and path.startswith(
        (
            "backend/app/",
            "backend/tests/",
            "backend/migrations/",
            "frontend/",
            "docker/",
            "compose",
            ".env",
            "backend/.env",
        )
    )


def verify_c9_additions(files):
    if digest(C9_PROOF) != C9_PROOF_SHA256:
        raise ValueError("Frozen C9 proof changed")
    for path, expected in FROZEN_C9_ADDITIONS.items():
        if digest(ROOT / path) != expected:
            raise ValueError("Frozen C9 source/evidence changed: " + path)
    return files | FROZEN_C9_ADDITIONS


def validate_c10_parent(baseline, proof):
    parents = {r["path"]: r["sha256"] for r in baseline["files"]}
    if (
        baseline.get("unit") != "SQL-C10"
        or proof.get("stage") != "SQL-C10"
        or baseline.get("previous_checkpoint_sha256") != C9_PROOF_SHA256
        or proof.get("previous_checkpoint_sha256") != C9_PROOF_SHA256
        or digest(C9_PROOF) != C9_PROOF_SHA256
        or parents.get("docs/adaptation/sql/sql_c9_validation.json") != C9_PROOF_SHA256
    ):
        raise ValueError("C10 parent C9 is missing or changed")


def append_c10_checkpoint(checkpoints):
    if not C10_PROOF.is_file():
        return checkpoints
    document, proof = read(C10_BASELINE), read(C10_PROOF)
    validate_c10_parent(document, proof)
    validate_proof(
        "SQL-C10", "accepted_contract_defined_offline", proof, digest(C10_BASELINE)
    )
    if digest(C10_REFERENCES) != proof.get("reference_baseline_sha256"):
        raise ValueError("C10 reference supplement changed")
    references = read(C10_REFERENCES)
    if references.get("initial_baseline_sha256") != digest(C10_BASELINE):
        raise ValueError("C10 supplement has different parent")
    baseline = {r["path"]: r["sha256"] for r in document["files"]}
    additions = {r["path"]: r["sha256"] for r in references["files"]}
    if set(baseline) & set(additions):
        raise ValueError("C10 supplement replaces initial inputs")
    baseline |= additions
    preserve_latest_baseline(
        baseline, checkpoints, proof.get("inherited_postimages", {})
    )
    verify_c9_additions({})
    checkpoints.append(
        {
            "stage": "SQL-C10",
            "status": proof["status"],
            "baseline_path": C10_BASELINE,
            "proof_path": C10_PROOF,
            "baseline": {
                **document,
                "files": [{"path": p, "sha256": s} for p, s in baseline.items()],
            },
            "changes": stage_changes("SQL-C10", baseline, proof, C10_PROOF),
        }
    )
    return checkpoints


def all_later_checkpoints(checkpoints):
    return append_c11_checkpoint(
        append_c10_checkpoint(append_c9_checkpoint(checkpoints))
    )


def self_test_c10():
    baseline = {
        "unit": "SQL-C10",
        "previous_checkpoint_sha256": C9_PROOF_SHA256,
        "files": [
            {
                "path": "docs/adaptation/sql/sql_c9_validation.json",
                "sha256": C9_PROOF_SHA256,
            }
        ],
    }
    proof = {"stage": "SQL-C10", "previous_checkpoint_sha256": C9_PROOF_SHA256}
    validate_c10_parent(baseline, proof)
    rejected = 0
    for altered, altered_proof in (
        ({**baseline, "unit": "SQL-C9"}, proof),
        ({**baseline, "files": []}, proof),
        ({**baseline, "previous_checkpoint_sha256": "a" * 64}, proof),
        (baseline, {**proof, "stage": "SQL-C9"}),
        (baseline, {**proof, "previous_checkpoint_sha256": "a" * 64}),
    ):
        try:
            validate_c10_parent(altered, altered_proof)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("C10 accepted a changed parent")
    for path in (
        "backend/app/main.py",
        "frontend/src/App.tsx",
        "backend/migrations/999_bad.sql",
        "compose.channels-ui.yaml",
        "docs/adaptation/fragments/sql-c9.json",
    ):
        before = digest(ROOT / path)
        try:
            stage_changes(
                "SQL-C10",
                {path: before},
                {
                    "changed_files": [
                        {
                            "path": path,
                            "before_sha256": before,
                            "after_sha256": "a" * 64,
                        }
                    ]
                },
                C10_PROOF,
            )
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("C10 accepted runtime or closed evidence mutation")
    print(
        "C10 contract-only history checks passed; "
        + str(rejected)
        + " unsafe transitions rejected"
    )
# C11 is an additive physical-schema checkpoint; closed C10 bytes remain exact.
def verify_previous_assets(files):
    return verify_c9_additions(verify_c8_additions(verify_c7_additions(files)))


C11_BASELINE = DOCS / "sql_c11_input_baseline.json"
C11_PROOF = DOCS / "sql_c11_validation.json"
C10_PROOF_SHA256 = "a4ab948bafe0349b9b8695b0d4258a891da383d238cad5a3c3c9b9de2a030934"
C11_RELEASE = "backend/migrations/cbn_channels_parity_v1/release.json"
C11_RELEASE_SHA256 = "f5200dad8a3f8295bc2bbaf71ed6feecf2c847eab5e8031fc86038c94e9c2e32"
FROZEN_C10_ADDITIONS = {
    "artifacts/sql-c10/graph-diagnostics.json": (
        "4682929fc2a676b65d14168ec657aaae42b3a693e217e0097cb1a4e03e7e36cf"
    ),
    "artifacts/sql-c10/link-checks.json": (
        "ac71d89fdf4f2b960e092a23bd66e4cd46093cf0f2f6da8a6556d942e8798a78"
    ),
    "artifacts/sql-c10/offline-checks.json": (
        "518695e7d03b9c96c2109e8ec16d7a0ca39f63f8d18f7a9abf374cfb3c114439"
    ),
    "artifacts/sql-c10/review-oauth.json": (
        "34a3fc7dd5bae544700be6dd27e79db15e7457371e68cf8b9f8d89e59d12a67a"
    ),
    "artifacts/sql-c10/review-tiktok.json": (
        "589758f1e6ea150f307b27a023be7c0edb4ccbcdddbd98af6b52ec1fb2290c4e"
    ),
    "artifacts/sql-c10/review-webhooks.json": (
        "3d263fc8ef04581e0e220ab13028cd6cd65ccaea435ef237c2c9426633867b23"
    ),
    "artifacts/sql-c10/source-oauth.json": (
        "46200241f475e348238a7b0d5dab8620a2d5f4b5740b9040609ea21155b87bf0"
    ),
    "artifacts/sql-c10/source-tiktok.json": (
        "123e53757146108c273453ab53f858101aef5a6ebb623f6a9ae1b11784fe611a"
    ),
    "artifacts/sql-c10/source-webhooks-secrets.json": (
        "d1df93694080c45c4d10ce0c4b168af568cc33e59bbb65bdf3aeda5fbdb66da5"
    ),
    "docs/adaptation/fragments/sql-c10.json": (
        "5cc71ee00639def2f7acea6199900a7a39f28f80e632e5e6a58212cc40bbc36a"
    ),
    "docs/adaptation/sql/SQL_C10_CONTRACT.md": (
        "897eb598ff28aca9dd9f7ae097711b2b3086647d53afa35fee96ebe256b3f4af"
    ),
    "docs/adaptation/sql/SQL_C10_FIELD_MATRIX.md": (
        "ce44c6970dff8092dad23ec313bb27a2804f0dd5922dd18f71c10ba6bc0478ec"
    ),
    "docs/adaptation/sql/SQL_C10_REVIEW.md": (
        "a92ed608d97cfef4205c6d1a72c06b72732b596a8db73ec52af93f8482fb8a15"
    ),
    "docs/adaptation/sql/channels-parity-contract.json": (
        "376f5f1234347cd403fe9a71fb0c4421fa14f2eee552afc790e91ae95a1cd7ba"
    ),
    "docs/adaptation/sql/channels-ui-parity-contract.json": (
        "7beee8a73c8292e4fc7d78162a5733805199d7d555c7f3df0f2e65eb28878842"
    ),
    "docs/adaptation/sql/check_c10_contract.py": (
        "f62862abc7182c7c373c30290ca84cca90a8b554dde794989b286dc842d0ce15"
    ),
    "docs/decisions/ADR-022-channels-parity-contract.md": (
        "4d34aff9929b4a139f6373d524524ddf9ec5f61625b5bc71aba09e721c8ad357"
    ),
    "tasks/sql-c10-progress.json": (
        "a85ed40c55d89450118ff127abe89874c8bb38a22da3bdb803d05018d6c09f52"
    ),
    "docs/adaptation/sql/sql_c10_input_baseline.json": (
        "11abae86cd301fe5e349088b9016dc14f60bf90de792ee5ead0d19c645489dac"
    ),
    "docs/adaptation/sql/sql_c10_reference_baseline.json": (
        "910073681c9fbcedd80cb4a9e12b24ee09cfdbfd5bcf9d5681370e3e99d2571b"
    ),
    "docs/adaptation/sql/sql_c10_validation.json": (
        "a4ab948bafe0349b9b8695b0d4258a891da383d238cad5a3c3c9b9de2a030934"
    ),
}
C11_RELEASE_FILES = {r["path"]: r["sha256"] for r in read(ROOT / C11_RELEASE)["files"]}
C11_RELEASE_FILES[C11_RELEASE] = C11_RELEASE_SHA256
C11_FROZEN = set(FROZEN_C10_ADDITIONS) | set(C11_RELEASE_FILES)
ADDITIVE_STAGES = {"SQL-C7", "SQL-C8", "SQL-C9", "SQL-C10", "SQL-C11"}
COMPOSE_STAGES = {"SQL-C5", *ADDITIVE_STAGES}


def stage_forbidden_change(stage, path):
    return c10_forbidden_change(stage, path) or (
        stage == "SQL-C11"
        and (
            path.startswith(
                (
                    "backend/app/",
                    "frontend/",
                    "docker/",
                    "compose",
                    ".env",
                    "backend/.env",
                )
            )
            or (
                path.startswith("backend/migrations/") and path not in C11_RELEASE_FILES
            )
        )
    )


def verify_c11_assets(files):
    if (
        digest(C10_PROOF) != C10_PROOF_SHA256
        or digest(ROOT / C11_RELEASE) != C11_RELEASE_SHA256
    ):
        raise ValueError("Frozen C10 proof/C11 release changed")
    for name, expected in {**FROZEN_C10_ADDITIONS, **C11_RELEASE_FILES}.items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen C10/C11 schema asset changed: " + name)
    return files | FROZEN_C10_ADDITIONS | C11_RELEASE_FILES


def validate_c11_parent(baseline, proof):
    parents = {r["path"]: r["sha256"] for r in baseline["files"]}
    if (
        baseline.get("unit") != "SQL-C11"
        or proof.get("stage") != "SQL-C11"
        or baseline.get("previous_checkpoint_sha256") != C10_PROOF_SHA256
        or proof.get("previous_checkpoint_sha256") != C10_PROOF_SHA256
        or parents.get("docs/adaptation/sql/sql_c10_validation.json")
        != C10_PROOF_SHA256
        or digest(C10_PROOF) != C10_PROOF_SHA256
    ):
        raise ValueError("C11 parent C10 missing or changed")


def append_c11_checkpoint(checkpoints):
    if not C11_PROOF.is_file():
        return checkpoints
    baseline, proof = read(C11_BASELINE), read(C11_PROOF)
    validate_c11_parent(baseline, proof)
    validate_proof(
        "SQL-C11",
        "accepted_restored_channels_parity_schema_only",
        proof,
        digest(C11_BASELINE),
    )
    if proof.get("release_sha256") != C11_RELEASE_SHA256:
        raise ValueError("C11 release evidence changed")
    files = {r["path"]: r["sha256"] for r in baseline["files"]}
    preserve_latest_baseline(files, checkpoints, proof.get("inherited_postimages", {}))
    verify_c11_assets({})
    checkpoints.append(
        {
            "stage": "SQL-C11",
            "status": proof["status"],
            "baseline_path": C11_BASELINE,
            "proof_path": C11_PROOF,
            "baseline": baseline,
            "changes": stage_changes("SQL-C11", files, proof, C11_PROOF),
        }
    )
    return checkpoints


def self_test_c11():
    baseline = {
        "unit": "SQL-C11",
        "previous_checkpoint_sha256": C10_PROOF_SHA256,
        "files": [
            {
                "path": "docs/adaptation/sql/sql_c10_validation.json",
                "sha256": C10_PROOF_SHA256,
            }
        ],
    }
    proof = {"stage": "SQL-C11", "previous_checkpoint_sha256": C10_PROOF_SHA256}
    validate_c11_parent(baseline, proof)
    rejected = 0
    for bad, badproof in (
        ({**baseline, "unit": "SQL-C10"}, proof),
        ({**baseline, "files": []}, proof),
        ({**baseline, "previous_checkpoint_sha256": "a" * 64}, proof),
        (baseline, {**proof, "stage": "SQL-C10"}),
        (baseline, {**proof, "previous_checkpoint_sha256": "a" * 64}),
    ):
        try:
            validate_c11_parent(bad, badproof)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("C11 changed parent accepted")
    for path in (
        "backend/app/main.py",
        "frontend/src/App.tsx",
        "compose.channels-ui.yaml",
        "docs/adaptation/sql/channels-parity-contract.json",
        "backend/migrations/011_channels.sql",
        "backend/migrations/999_unapproved.sql",
    ):
        before = digest(ROOT / path)
        try:
            stage_changes(
                "SQL-C11",
                {path: before},
                {
                    "changed_files": [
                        {
                            "path": path,
                            "before_sha256": before,
                            "after_sha256": "a" * 64,
                        }
                    ]
                },
                C11_PROOF,
            )
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("C11 frozen/runtime/unknown SQL mutation accepted")
    path = "backend/migrations/cbn_channels_parity_v1/CBN-CHP001.sql"
    after = C11_RELEASE_FILES[path]
    assert stage_changes(
        "SQL-C11",
        {},
        {
            "changed_files": [
                {"path": path, "before_sha256": None, "after_sha256": after}
            ]
        },
        C11_PROOF,
    )
    print(
        "C11 additive schema checks passed; "
        + str(rejected)
        + " unsafe transitions rejected"
    )



# SQL-C12 is additive; all released C11 files and prior previews stay pinned.
C12_BASELINE = DOCS / "sql_c12_input_baseline.json"
C12_PROOF = DOCS / "sql_c12_validation.json"
C11_PROOF_SHA256 = "d4e90466b829487e63ce3856d2be78cc97b88f588e30ab9c58ab73caaf34f2fb"
FROZEN_C11_ADDITIONS = {
    "artifacts/sql-c11/constraints-result.json": (
        "5b5cceaaa6404169a64ffdc1d6102d56908b3f1685b6992709d365809ba9d605"
    ),
    "artifacts/sql-c11/faults-result.json": (
        "3be78f2195b175a7f6ed064dfad7bc30b0412853601b51a6768d46f5958c8a21"
    ),
    "artifacts/sql-c11/graph-diagnostics.json": (
        "4807a75ac8a6d312367b48001b05d7fe7c6c7becb842ca6ed837dea1493e6902"
    ),
    "artifacts/sql-c11/legacy-readiness.json": (
        "969e80ec66c5133d1d7ee975f51817fa38e50904cf4d72c6c224e574841a274e"
    ),
    "artifacts/sql-c11/link-checks.json": (
        "f2bfc024dc7c32d36f6244e9269291e940c15ae0faa5c9225369a3fefcaa2631"
    ),
    "artifacts/sql-c11/offline-checks.json": (
        "482f842931953d722c88f563f8dfe5cd73482c6f91bb0077292809cdbd79b27e"
    ),
    "artifacts/sql-c11/offline-results.xml": (
        "e93696742ef261b3266ebe0c5f031c6e039cf3f3a56d67d24c3902b715aee01e"
    ),
    "artifacts/sql-c11/preservation.json": (
        "2c8399982ee4e54573765051a996e100eed674bda4bf2d2f390227c88587997a"
    ),
    "artifacts/sql-c11/previews.json": (
        "f8fb6a92bb87f2fc183795e975541b4244727fd16c64f4297143177ae5216acd"
    ),
    "artifacts/sql-c11/reference-result.json": (
        "69a55450441e8ae1ea2d527ce3e301fa214dae1fa8046896eb4d0c69b2394810"
    ),
    "artifacts/sql-c11/release-check.json": (
        "ef566999ec4d151215116f4481426ea7ec16eb4b3e76ec72bb713e7e9826f505"
    ),
    "artifacts/sql-c11/review.json": (
        "67d6d72beae63f9b2ea6bfc8d3acbcd94f2ee32e031924396250bbab0b79c958"
    ),
    "artifacts/sql-c11/trial-result.json": (
        "1adc509c3d8b22b5f78c07526354efcbe8d78aeece960fcc4889c58a4118563c"
    ),
    ("backend/migrations/cbn_channels_parity_v1/CBN-CHP001.sql"): (
        "5263d2d6418f368e2fce0a16d5fd35a9de69b975dc4e42f3b1f732236605b47c"
    ),
    ("backend/migrations/cbn_channels_parity_v1/CBN-CHP002.sql"): (
        "3f6291e00cc2996c10fd1b92d7fcf55277377676db0cf515c95dc4ecc0a608c2"
    ),
    ("backend/migrations/cbn_channels_parity_v1/CBN-CHP003.sql"): (
        "098673dae67bb98a645e37f7db640cf8b7d616db736d4776ee7c580699655af7"
    ),
    ("backend/migrations/cbn_channels_parity_v1/CBN-CHP004.sql"): (
        "fcbc04ea5c26740757b0121a5848255d5e0f95e30cce1f07e846dfa51beb4dca"
    ),
    ("backend/migrations/cbn_channels_parity_v1/CBN-CHP005.sql"): (
        "a503dea27675372b769e48be4a44a216dfcaa4a8962ea41f01b47b39dbcbf866"
    ),
    ("backend/migrations/cbn_channels_parity_v1/constraint-coverage.json"): (
        "9890ee9cbc1be5e634b75fe796464777e0e6c116dcf543b1daa95dfdd60b0e36"
    ),
    ("backend/migrations/cbn_channels_parity_v1/expected-shapes.json"): (
        "994c0615e4121aef87cad4791536b540be1f22844ffd20ba21e32116b240ec1c"
    ),
    ("backend/migrations/cbn_channels_parity_v1/release.json"): (
        "f5200dad8a3f8295bc2bbaf71ed6feecf2c847eab5e8031fc86038c94e9c2e32"
    ),
    ("backend/migrations/cbn_channels_parity_v1/reviewed-checks.json"): (
        "c60ee1e72d8d425555b7c3e44984939028edb5401af2cfb3adba0a81f373c359"
    ),
    ("backend/tests/test_channels_parity_migrations.py"): (
        "2e88dda11571498e1c72439b2ca608db1683244126d5db0bf41bb58c5071b3fc"
    ),
    "backend/tools/channels_parity.py": (
        "3e36f45ae448127cc44b67eae0aa3ea942957b62bd0bcba2c4f811a2f44a35e2"
    ),
    "backend/tools/channels_parity_contract.py": (
        "b80f48c2b7cdf5c223b45281cc69fb9581876808cd19d279141841b54ab31a61"
    ),
    "backend/tools/channels_parity_snapshot.py": (
        "9303c95645d94f343bd396710f43deb121b98a36a13d212f8f84a4e110c14e03"
    ),
    "backend/tools/check_channels_parity.py": (
        "d81061829609453becac7c4861b063a8230486a2550b04464131be60c9411070"
    ),
    "backend/tools/rehearse_channels_parity.py": (
        "b29c16d14d83ff0af9d7cedef5cb828d59df9196fc8b957f141f8cc33cd3ccf9"
    ),
    ("backend/tools/rehearse_channels_parity_faults.py"): (
        "5cc71776c46b99750ec8dedbf2eeea2687671a89b41d54a38bdc1210b9ca013b"
    ),
    "docs/adaptation/fragments/sql-c11.json": (
        "796603d83abb10246f6d41fb09987ac14eacf675cf42fda922603e676b6ff008"
    ),
    "docs/adaptation/sql/SQL_C11_REVIEW.md": (
        "ed4fcbbc67cf9647af9cec3ea79f22dc1c81f718cd55ee98cf0fd87253d0c518"
    ),
    ("docs/decisions/ADR-023-channels-parity-schema-rehearsal.md"): (
        "0d37b4d8154aff56e66e87bdafb4092f5c05da122d7235a273d6edb775db643a"
    ),
    "tasks/sql-c11-progress.json": (
        "337bd17918e22c5fb11ab1d82f58ffe863aaa68ff9cb7d690469566de70c1f79"
    ),
    "docs/adaptation/sql/sql_c11_validation.json": (
        "d4e90466b829487e63ce3856d2be78cc97b88f588e30ab9c58ab73caaf34f2fb"
    ),
}
_c11_later_frozen = later_frozen
_c11_channel_assets = channel_assets
_c11_stage_forbidden = stage_forbidden_change
_c11_all_checkpoints = all_later_checkpoints
ADDITIVE_STAGES.add("SQL-C12")
COMPOSE_STAGES.add("SQL-C12")


def later_frozen(path):
    return _c11_later_frozen(path) or path in FROZEN_C11_ADDITIONS


def channel_assets():
    assets = _c11_channel_assets()
    for name, expected in FROZEN_C11_ADDITIONS.items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen C11 evidence changed: " + name)
    return assets | FROZEN_C11_ADDITIONS


def stage_forbidden_change(stage, path):
    return _c11_stage_forbidden(stage, path) or (
        stage == "SQL-C12"
        and (
            path.startswith(
                (
                    "frontend/",
                    "docker/",
                    "compose",
                    ".env",
                    "backend/.env",
                    "backend/migrations/",
                )
            )
            or (
                path.startswith("backend/app/")
                and not path.startswith("backend/app/parity_channels/")
            )
        )
    )


def validate_c12_parent(baseline, proof):
    parents = {r["path"]: r["sha256"] for r in baseline["files"]}
    if (
        baseline.get("unit") != "SQL-C12"
        or proof.get("stage") != "SQL-C12"
        or baseline.get("previous_checkpoint_sha256") != C11_PROOF_SHA256
        or proof.get("previous_checkpoint_sha256") != C11_PROOF_SHA256
        or parents.get("docs/adaptation/sql/sql_c11_validation.json")
        != C11_PROOF_SHA256
        or digest(C11_PROOF) != C11_PROOF_SHA256
    ):
        raise ValueError("C12 accepted C11 parent missing or changed")


def all_later_checkpoints(checkpoints):
    checkpoints = _c11_all_checkpoints(checkpoints)
    if not C12_PROOF.is_file():
        return checkpoints
    baseline, proof = read(C12_BASELINE), read(C12_PROOF)
    validate_c12_parent(baseline, proof)
    validate_proof(
        "SQL-C12",
        "accepted_restored_channels_mappings_repositories_only",
        proof,
        digest(C12_BASELINE),
    )
    files = {r["path"]: r["sha256"] for r in baseline["files"]}
    preserve_latest_baseline(files, checkpoints, proof.get("inherited_postimages", {}))
    channel_assets()
    checkpoints.append(
        {
            "stage": "SQL-C12",
            "status": proof["status"],
            "baseline_path": C12_BASELINE,
            "proof_path": C12_PROOF,
            "baseline": baseline,
            "changes": stage_changes("SQL-C12", files, proof, C12_PROOF),
        }
    )
    return checkpoints


def self_test_c12():
    baseline = {
        "unit": "SQL-C12",
        "previous_checkpoint_sha256": C11_PROOF_SHA256,
        "files": [
            {
                "path": "docs/adaptation/sql/sql_c11_validation.json",
                "sha256": C11_PROOF_SHA256,
            }
        ],
    }
    proof = {"stage": "SQL-C12", "previous_checkpoint_sha256": C11_PROOF_SHA256}
    validate_c12_parent(baseline, proof)
    rejected = 0
    for bad, badproof in (
        ({**baseline, "unit": "SQL-C11"}, proof),
        ({**baseline, "files": []}, proof),
        ({**baseline, "previous_checkpoint_sha256": "a" * 64}, proof),
        (baseline, {**proof, "stage": "SQL-C11"}),
        (baseline, {**proof, "previous_checkpoint_sha256": "a" * 64}),
    ):
        try:
            validate_c12_parent(bad, badproof)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("C12 changed parent accepted")
    for path in (
        "backend/app/main.py",
        "backend/app/channels_ui_app.py",
        "frontend/src/App.tsx",
        "compose.channels-ui.yaml",
        "backend/migrations/999_unapproved.sql",
        "backend/tools/channels_parity.py",
        "docs/adaptation/fragments/sql-c11.json",
        "tasks/sql-c11-progress.json",
        "docs/adaptation/sql/sql_c11_validation.json",
    ):
        before = digest(ROOT / path)
        try:
            stage_changes(
                "SQL-C12",
                {path: before},
                {
                    "changed_files": [
                        {
                            "path": path,
                            "before_sha256": before,
                            "after_sha256": "a" * 64,
                        }
                    ]
                },
                C12_PROOF,
            )
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("C12 old runtime/schema/evidence changed")
    assert stage_changes(
        "SQL-C12",
        {},
        {
            "changed_files": [
                {
                    "path": "backend/app/parity_channels/new.py",
                    "before_sha256": None,
                    "after_sha256": "a" * 64,
                }
            ]
        },
        C12_PROOF,
    )
    print(
        "C12 additive repository checks passed; "
        + str(rejected)
        + " unsafe transitions rejected"
    )



# SQL-C13 adds a general composition; previous previews remain immutable.
C13_BASELINE = DOCS / "sql_c13_input_baseline.json"
C13_PROOF = DOCS / "sql_c13_validation.json"
C12_PROOF_SHA256 = "e31996022ae84c19d5f5f1f81f95b7f337d43d29cc384163f0055d04b719f477"
FROZEN_C12_ADDITIONS = {
    "artifacts/sql-c12/connected-result.json": (
        "67138b3d56c9a4a19d269b3cb64c8815dd6ba20d7838e67945f9ac135a72e8d9"
    ),
    "artifacts/sql-c12/graph-checks.json": (
        "a69d469a91c8c84369e6d3d1caa8edefa44bbe16e9a54891d52df415fda1aeb0"
    ),
    "artifacts/sql-c12/link-checks.json": (
        "28773d924a6475696cdb4b5693b7b98e0dec8d1ef053fa1159bdbf3f5c983774"
    ),
    "artifacts/sql-c12/offline-checks.json": (
        "1c0860ffeedfcb1889d75d5c3fcf286f3fa1d234ca843a7055a0c3690c39fc60"
    ),
    "artifacts/sql-c12/preservation.json": (
        "983e683a470190ee9d3f038500b3d4891ab88f7eea24b895163fb3a5bd8b607a"
    ),
    "artifacts/sql-c12/previews.json": (
        "f8fb6a92bb87f2fc183795e975541b4244727fd16c64f4297143177ae5216acd"
    ),
    "artifacts/sql-c12/progress-review.json": (
        "d40410b6cfcc8bc82eb1a934003699824ce61995ec1df620473eed9824340968"
    ),
    "artifacts/sql-c12/review.json": (
        "b1bba9ac8eb3fccbf5339a23dff27a4ae8c9f6094c330b5e500c360cd7980495"
    ),
    "backend/app/parity_channels/__init__.py": (
        "e831fadc1b1998d7fb072ab1c17dc96bc245acbdc2b7b9a121dfbda1ef6d9814"
    ),
    "backend/app/parity_channels/api.py": (
        "76d1cbca1a1ac7ed1efa6e1ba18a79d22c1db21344a7085891cad0bc35aacee6"
    ),
    "backend/app/parity_channels/catalog.py": (
        "855dc648346030fcd81e52815d8e911121900f2f4b24602dfae7e7d57951be3b"
    ),
    "backend/app/parity_channels/guard.py": (
        "698a16fb64cf6a6ebe61d2afa23f69820d5ea6531571d5e4c3f2d287f8168230"
    ),
    "backend/app/parity_channels/policy.py": (
        "8622d45db43a3328e9d485b5561ac0bfc0ac6162849a79c31e0a9a50dd792830"
    ),
    "backend/app/parity_channels/profile.py": (
        "d84372dc77f06761bd0fdf333557c08e003373ca455bb27e81ed5427b0824c7a"
    ),
    "backend/app/parity_channels/repository.py": (
        "90a0c51418c474bf94da4369518b21e617673612c7872141ca2e72bb694cad63"
    ),
    "backend/tests/test_parity_channels.py": (
        "74fda7ea8521c93526bcc62f0c5c803ba7365235c660fc9aa89b154110d7bae5"
    ),
    "backend/tools/check_parity_repositories.py": (
        "5b35bafe567fb840fd5b0bda7104eba3d8740b90b0a7277ed85c259107b73b41"
    ),
    "backend/tools/check_phase_progress.py": (
        "7502d284b7fb88c889b37303212451252d7c9fc3ef9da9538107db444368a2c7"
    ),
    "backend/tools/fault_parity_repositories.py": (
        "859fd6394ef9320befa3c4b494e37378fec66d1f29b10736bb5ea05ac28c9de1"
    ),
    "backend/tools/parity_data.py": (
        "02065a9eecc84a0df78cbf2b6ee384ba224e7515083a257339f0599f5e549626"
    ),
    "backend/tools/parity_mapping.py": (
        "7c21b4bdb51b0d82aca607963d4e05e99fbf4254d4eea7e1926a1d2eea3b68bb"
    ),
    ("backend/tools/rehearse_parity_repositories.py"): (
        "d83db9774ab6ff6bbd69f83d6dd722d5719e1f4b63666fb2726f74becd766397"
    ),
    "docs/adaptation/fragments/sql-c12.json": (
        "25714a73a60b005ea3906997a684677a2c3396642370e12d79da56aa54c9a32a"
    ),
    "docs/adaptation/sql/SQL_C12_REVIEW.md": (
        "9447e29ea34bbe6457f5e19831ba6e391b60889df7bb000f0e4a51998f17fdef"
    ),
    ("docs/decisions/ADR-024-channels-parity-repositories.md"): (
        "757c8fa36ddefeb1ec14d9499ae0f8954803f2923bfdd39e246bda87462a6bcb"
    ),
    "tasks/sql-c12-progress.json": (
        "f90a247b79f402e4479ba9f086fa7df922fd61d833ef2c2c8a965191dcaa54d9"
    ),
    "docs/adaptation/sql/sql_c12_validation.json": (
        "e31996022ae84c19d5f5f1f81f95b7f337d43d29cc384163f0055d04b719f477"
    ),
}
_c12_later_frozen = later_frozen
_c12_channel_assets = channel_assets
_c12_stage_forbidden = stage_forbidden_change
_c12_all_checkpoints = all_later_checkpoints
ADDITIVE_STAGES.add("SQL-C13")
COMPOSE_STAGES.add("SQL-C13")


def later_frozen(path):
    return _c12_later_frozen(path) or path in FROZEN_C12_ADDITIONS


def channel_assets():
    assets = _c12_channel_assets()
    for name, expected in FROZEN_C12_ADDITIONS.items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen C12 evidence changed: " + name)
    return assets | FROZEN_C12_ADDITIONS


def stage_forbidden_change(stage, path):
    return _c12_stage_forbidden(stage, path) or (
        stage == "SQL-C13"
        and (
            path.startswith(("backend/migrations/", ".env", "backend/.env"))
            or path
            in {
                "Dockerfile",
                ".dockerignore",
                "frontend/src/App.tsx",
                "frontend/src/main.tsx",
                "frontend/package.json",
                "frontend/package-lock.json",
            }
            or (
                path.startswith("backend/app/")
                and not path.startswith("backend/app/general_preview/")
            )
            or (
                path.startswith("frontend/src/")
                and not path.startswith("frontend/src/general/")
            )
            or (
                path.startswith("docker/")
                and path
                not in {
                    "docker/Dockerfile.general",
                    "docker/Dockerfile.general.dockerignore",
                    "docker/general-start.sh",
                    "docker/nginx.general.conf",
                }
            )
            or (path.startswith("compose") and path != "compose.general.yaml")
        )
    )


def validate_c13_parent(baseline, proof):
    parents = {r["path"]: r["sha256"] for r in baseline["files"]}
    if (
        baseline.get("unit") != "SQL-C13"
        or proof.get("stage") != "SQL-C13"
        or baseline.get("previous_checkpoint_sha256") != C12_PROOF_SHA256
        or proof.get("previous_checkpoint_sha256") != C12_PROOF_SHA256
        or parents.get("docs/adaptation/sql/sql_c12_validation.json")
        != C12_PROOF_SHA256
        or digest(C12_PROOF) != C12_PROOF_SHA256
    ):
        raise ValueError("C13 accepted C12 parent missing or changed")


def all_later_checkpoints(checkpoints):
    checkpoints = _c12_all_checkpoints(checkpoints)
    if not C13_PROOF.is_file():
        return checkpoints
    baseline, proof = read(C13_BASELINE), read(C13_PROOF)
    validate_c13_parent(baseline, proof)
    validate_proof(
        "SQL-C13", "accepted_general_preview_and_P1_4_only", proof, digest(C13_BASELINE)
    )
    files = {r["path"]: r["sha256"] for r in baseline["files"]}
    preserve_latest_baseline(files, checkpoints, proof.get("inherited_postimages", {}))
    channel_assets()
    checkpoints.append(
        {
            "stage": "SQL-C13",
            "status": proof["status"],
            "baseline_path": C13_BASELINE,
            "proof_path": C13_PROOF,
            "baseline": baseline,
            "changes": stage_changes("SQL-C13", files, proof, C13_PROOF),
        }
    )
    return checkpoints


def self_test_c13():
    baseline = {
        "unit": "SQL-C13",
        "previous_checkpoint_sha256": C12_PROOF_SHA256,
        "files": [
            {
                "path": "docs/adaptation/sql/sql_c12_validation.json",
                "sha256": C12_PROOF_SHA256,
            }
        ],
    }
    proof = {"stage": "SQL-C13", "previous_checkpoint_sha256": C12_PROOF_SHA256}
    validate_c13_parent(baseline, proof)
    rejected = 0
    for bad, badproof in (
        ({**baseline, "unit": "SQL-C12"}, proof),
        ({**baseline, "files": []}, proof),
        ({**baseline, "previous_checkpoint_sha256": "a" * 64}, proof),
        (baseline, {**proof, "stage": "SQL-C12"}),
        (baseline, {**proof, "previous_checkpoint_sha256": "a" * 64}),
    ):
        try:
            validate_c13_parent(bad, badproof)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("C13 changed parent accepted")
    for path in (
        "backend/app/main.py",
        "backend/app/parity_channels/profile.py",
        "frontend/src/App.tsx",
        "frontend/src/shared/runtimeCapabilities.tsx",
        "Dockerfile",
        ".dockerignore",
        "compose.channels-ui.yaml",
        "backend/migrations/999_unapproved.sql",
        "docs/adaptation/fragments/sql-c12.json",
        "docs/adaptation/sql/sql_c12_validation.json",
    ):
        before = digest(ROOT / path)
        try:
            stage_changes(
                "SQL-C13",
                {path: before},
                {
                    "changed_files": [
                        {
                            "path": path,
                            "before_sha256": before,
                            "after_sha256": "a" * 64,
                        }
                    ]
                },
                C13_PROOF,
            )
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("C13 historical runtime/evidence changed")
    for path in (
        "backend/app/general_preview/new.py",
        "frontend/src/general/new.tsx",
        "compose.general.yaml",
        "docker/Dockerfile.general",
    ):
        assert stage_changes(
            "SQL-C13",
            {},
            {
                "changed_files": [
                    {"path": path, "before_sha256": None, "after_sha256": "a" * 64}
                ]
            },
            C13_PROOF,
        )
    print(
        "C13 additive composition checks passed; "
        + str(rejected)
        + " unsafe transitions rejected"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        self_test_c9()
        self_test_c10()
        self_test_c11()
        self_test_c12()
        self_test_c13()
    else:
        accepted = verify_active_checkpoint()
        print(
            "Frozen C3 verified; active historical chain "
            + ("verified" if accepted else "not yet recorded")
        )
