"""Independent legacy-contract inspection and rollback-only SQL integrity checks."""

import json
import re
import uuid

from tools.cbn_foundation import ROOT, require
from tools.foundation_snapshot import metadata

JOURNAL_COLUMNS = [
    ("EventId", "bigint", False, True),
    ("AttemptId", "uniqueidentifier", False, False),
    ("UnitId", "nvarchar(80)", False, False),
    ("EventKind", "varchar(32)", False, False),
    ("RecordedAtUtc", "datetime2(7)", False, False),
    ("ReleaseId", "nvarchar(80)", False, False),
    ("ToolVersion", "nvarchar(40)", False, False),
    ("ManifestSha256", "binary(32)", False, False),
    ("UnitSha256", "binary(32)", False, False),
    ("ShapeVersion", "varchar(32)", False, False),
    ("TargetSha256", "binary(32)", False, False),
    ("BeforeShapeSha256", "binary(32)", True, False),
    ("AfterShapeSha256", "binary(32)", True, False),
    ("EvidenceRef", "nvarchar(160)", False, False),
    ("ApprovalRef", "nvarchar(160)", False, False),
    ("BackupRef", "nvarchar(160)", False, False),
    ("PrincipalRef", "nvarchar(128)", False, False),
    ("ErrorCode", "varchar(60)", True, False),
    ("SuccessKey", "nvarchar(80)", True, False),
    ("RelatedAttemptId", "uniqueidentifier", True, False),
    ("RelatedUnitId", "nvarchar(80)", True, False),
]


def column_contract(actual, declared, collation):
    type_name, _, length = declared["type"].partition("(")
    length = length.rstrip(")")
    sizes = {
        "int": (4, 10, 0),
        "bigint": (8, 19, 0),
        "bit": (1, 1, 0),
        "uniqueidentifier": (16, 0, 0),
        "datetime2": (8, 27, 7),
    }
    if type_name in {"varchar", "nvarchar", "binary"}:
        size = (
            -1
            if length == "max"
            else int(length) * (2 if type_name == "nvarchar" else 1)
        )
        expected = (size, 0, 0)
    else:
        expected = sizes[type_name]
    require(
        actual["type_name"] == type_name
        and (actual["max_length"], actual["precision"], actual["scale"]) == expected,
        "reference_column_type_length_precision",
    )
    require(
        bool(actual["is_nullable"]) == declared["nullable"]
        and bool(actual["is_identity"]) == declared["identity"]
        and not actual["is_computed"],
        "reference_column_flags",
    )
    require(
        actual["collation_name"]
        == (collation if type_name in {"varchar", "nvarchar"} else None),
        "reference_column_collation",
    )
    if declared["identity"]:
        require(
            actual["identity_seed"] == "1" and actual["identity_increment"] == "1",
            "reference_identity",
        )
    definition = declared.get("definition", "")
    if "DEFAULT" in definition.upper() or declared["name"] == "RecordedAtUtc":
        normalized = re.sub(
            r"[\s\[\]()]", "", actual["default_definition"] or ""
        ).lower()
        require(normalized == "sysutcdatetime", "reference_utc_default")
        expected_name = (
            re.search(r"CONSTRAINT\s+(\w+)\s+DEFAULT", definition, re.I)[1]
            if definition
            else "DF_MigrationJournal_Recorded"
        )
        require(actual["default_name"] == expected_name, "reference_default_name")
    else:
        require(actual["default_definition"] is None, "unexpected_reference_default")


def inspect_reference(connection, collation):
    inventory = json.loads(
        (ROOT / "docs/adaptation/sql/inventory.json").read_text(encoding="utf-8")
    )
    expected_tables = [
        t
        for m in inventory["migrations"]
        if m["id"] in {"001", "006"}
        for t in m["tables"]
    ]
    shape = metadata(connection.cursor(), managed=True)
    require(
        {(s["name"], s["owner"]) for s in shape["schemas"]}
        == {("crm", "dbo"), ("crm_config", "dbo"), ("crm_meta", "dbo")},
        "reference_schema_owners",
    )
    tables = {
        o["schema_name"] + "." + o["name"]
        for o in shape["objects"]
        if o["type"].strip() == "U"
    }
    require(
        all(
            o["type"].strip() in {"U", "PK", "UQ", "C", "D", "F"}
            for o in shape["objects"]
        ),
        "reference_object_type_allowlist",
    )
    require(
        tables == {t["name"] for t in expected_tables} | {"crm_meta.MigrationJournal"},
        "reference_table_allowlist",
    )
    expected_columns = {t["name"]: t["columns"] for t in expected_tables}
    expected_columns["crm_meta.MigrationJournal"] = [
        {"name": n, "type": t, "nullable": null, "identity": ident}
        for n, t, null, ident in JOURNAL_COLUMNS
    ]
    expected_constraints = {
        "PK_MigrationJournal",
        "DF_MigrationJournal_Recorded",
        "CK_MigrationJournal_Event",
        "CK_MigrationJournal_Success",
        "CK_MigrationJournal_Error",
    }
    expected_indexes = {}
    for table in expected_tables:
        for col in table["columns"]:
            definition = col["definition"]
            expected_constraints.update(
                re.findall(r"\bCONSTRAINT\s+(\w+)", definition, re.I)
            )
            if "PRIMARY KEY" in definition or " UNIQUE" in definition:
                index = re.search(r"CONSTRAINT\s+(\w+)", definition)[1]
                pk = "PRIMARY KEY" in definition
                clustered = (
                    "NONCLUSTERED" not in definition
                    if pk
                    else "UNIQUE CLUSTERED" in definition
                )
                expected_indexes[(table["name"], index)] = (
                    "CLUSTERED" if clustered else "NONCLUSTERED",
                    pk,
                    not pk,
                    [col["name"]],
                    None,
                )
        for constraint in table["constraints"]:
            expected_constraints.update(
                re.findall(r"\bCONSTRAINT\s+(\w+)", constraint["definition"], re.I)
            )
    expected_indexes[("crm.Message", "IX_Message_Conversation_Sequence")] = (
        "NONCLUSTERED",
        False,
        False,
        ["ConversationId", "Sequence"],
        None,
    )
    expected_indexes[("crm_meta.MigrationJournal", "PK_MigrationJournal")] = (
        "CLUSTERED",
        True,
        False,
        ["EventId"],
        None,
    )
    expected_indexes[("crm_meta.MigrationJournal", "UX_MigrationJournal_Success")] = (
        "NONCLUSTERED",
        False,
        False,
        ["SuccessKey"],
        "successkeyisnotnull",
    )
    require(
        {
            o["name"]
            for o in shape["objects"]
            if o["type"].strip() in {"PK", "UQ", "C", "D", "F"}
        }
        == expected_constraints,
        "reference_constraint_allowlist",
    )
    for table, columns in expected_columns.items():
        actual = [
            c
            for c in shape["columns"]
            if c["schema_name"] + "." + c["table_name"] == table
        ]
        require(
            [c["name"] for c in actual] == [c["name"] for c in columns],
            "reference_column_order",
        )
        for a, c in zip(actual, columns, strict=True):
            column_contract(a, c, collation)
    indexes = {}
    for row in shape["indexes"]:
        indexes.setdefault(
            (row["schema_name"] + "." + row["table_name"], row["name"]), []
        ).append(row)
    require(set(indexes) == set(expected_indexes), "reference_index_allowlist")
    for key, rows in indexes.items():
        kind, pk, uq, columns, filter_expr = expected_indexes[key]
        first = rows[0]
        require(
            first["type_desc"] == kind
            and first["is_unique"]
            and bool(first["is_primary_key"]) == pk
            and bool(first["is_unique_constraint"]) == uq,
            "reference_index_properties",
        )
        require(
            [r["column_name"] for r in rows] == columns
            and all(
                r["key_ordinal"] == i
                and not r["is_descending_key"]
                and not r["is_included_column"]
                and not r["is_disabled"]
                and not r["ignore_dup_key"]
                for i, r in enumerate(rows, 1)
            ),
            "reference_index_columns",
        )
        actual_filter = (
            re.sub(r"[\s\[\]()]", "", first["filter_definition"] or "").lower() or None
        )
        require(actual_filter == filter_expr, "reference_index_filter")
    expected_fks = {
        (t["name"], f["source_columns"][0], f["target_table"], f["target_columns"][0])
        for t in expected_tables
        for f in t["foreign_keys"]
    }
    actual_fks = {
        (
            f["schema_name"] + "." + f["table_name"],
            f["column_name"],
            f["target_schema"] + "." + f["target_table"],
            f["target_column"],
        )
        for f in shape["foreign_keys"]
    }
    require(
        actual_fks == expected_fks and len(actual_fks) == 5, "reference_foreign_keys"
    )
    require(
        all(
            not f["is_disabled"]
            and not f["is_not_trusted"]
            and not f["is_not_for_replication"]
            and not f["delete_referential_action"]
            and not f["update_referential_action"]
            for f in shape["foreign_keys"]
        ),
        "reference_fk_trust_actions",
    )
    require(
        all(
            not c["is_disabled"]
            and not c["is_not_trusted"]
            and not c["is_not_for_replication"]
            for c in shape["checks"]
        ),
        "reference_check_trust",
    )
    require(not shape["triggers"], "reference_unexpected_trigger")
    require(
        {(p["schema_name"], p["name"], p["value"]) for p in shape["properties"]}
        == {
            ("crm_meta", "crm_meta.contract", "CBN-migrations-v1"),
            ("crm", "crm.contract", "CBN-foundation-B001-v1"),
            ("crm_config", "crm_config.contract", "CBN-foundation-B006-v1"),
        },
        "reference_markers",
    )
    return {
        "tables": len(tables),
        "columns": len(shape["columns"]),
        "indexes": len(indexes),
        "checks": len(shape["checks"]),
        "foreign_keys": len(actual_fks),
    }


def integrity_checks(connection):
    """Synthetic values and rollback only. No academic writes are attempted."""
    cursor = connection.cursor()
    checks = []

    def rejected(label, sql, params=(), state="23000"):
        try:
            cursor.execute(sql, *params)
        except Exception as error:
            require(
                error.args and error.args[0] == state, "wrong_integrity_error_" + label
            )
            checks.append(label)
        else:
            raise AssertionError("not_rejected_" + label)

    cursor.execute("SET XACT_ABORT OFF; BEGIN TRANSACTION;")
    try:
        contact, conversation, message, operation = [
            str(uuid.uuid4()) for _ in range(4)
        ]
        cursor.execute(
            """INSERT crm.Contact(ContactId,Name,Phone,City,Program,Schedule,Stage,Tags,
          Notes,Type,Interests,CustomValues)
          VALUES(?,'Synthetic probe','','','','','new','','','','','{}')""",
            contact,
        )
        cursor.execute(
            """INSERT crm.Conversation
          (ConversationId,ContactId,State,Priority,ControlMode,Unread)
          VALUES(?,?,'open','normal','human',0)""",
            conversation,
            contact,
        )
        cursor.execute(
            "INSERT crm.Message(MessageId,ConversationId,Body,Direction) "
            "VALUES(?,?,'probe','incoming')",
            message,
            conversation,
        )
        cursor.execute(
            """INSERT crm.Operation
          (OperationId,Action,PayloadHash,ContactId,ConversationId,Actor)
          VALUES(?,'create_contact',?,?,?,'local-operator')""",
            operation,
            bytes(32),
            contact,
            conversation,
        )
        for label, sql in [
            ("contact_identity", "UPDATE crm.Contact SET Name='',Phone='';"),
            ("contact_stage", "UPDATE crm.Contact SET Stage='';"),
            ("contact_json_object", "UPDATE crm.Contact SET CustomValues='[]';"),
            ("contact_json_valid", "UPDATE crm.Contact SET CustomValues='invalid';"),
            ("conversation_state", "UPDATE crm.Conversation SET State='invalid';"),
            (
                "conversation_priority",
                "UPDATE crm.Conversation SET Priority='invalid';",
            ),
            ("conversation_control", "UPDATE crm.Conversation SET ControlMode='bad';"),
            ("message_body", "UPDATE crm.Message SET Body=' ';"),
            ("message_direction", "UPDATE crm.Message SET Direction='invalid';"),
            ("operation_action", "UPDATE crm.Operation SET Action='invalid';"),
            ("operation_actor", "UPDATE crm.Operation SET Actor='invalid';"),
            (
                "operation_message",
                "UPDATE crm.Operation SET Action='add_message',MessageId=NULL;",
            ),
            (
                "configuration_json",
                "UPDATE crm_config.Configuration SET Document='invalid';",
            ),
            (
                "configuration_id",
                "UPDATE crm_config.Configuration SET ConfigurationId=2;",
            ),
            (
                "configuration_revision",
                "UPDATE crm_config.Configuration SET Revision=0;",
            ),
        ]:
            rejected(label, sql)
        for column, values in (
            ("State", ("open", "waiting", "closed")),
            ("Priority", ("low", "normal", "high", "urgent")),
            ("ControlMode", ("human", "ai")),
        ):
            for value in values:
                cursor.execute(f"UPDATE crm.Conversation SET {column}=?", value)
        for direction in ("incoming", "outgoing"):
            cursor.execute("UPDATE crm.Message SET Direction=?", direction)
        for action in ("create_contact", "edit_contact", "update_conversation"):
            cursor.execute("UPDATE crm.Operation SET Action=?,MessageId=NULL", action)
        cursor.execute(
            "UPDATE crm.Operation SET Action='add_message',MessageId=?", message
        )
        for label, table, column in (
            ("conversation_fk", "crm.Conversation", "ContactId"),
            ("message_fk", "crm.Message", "ConversationId"),
            ("operation_contact_fk", "crm.Operation", "ContactId"),
            ("operation_conversation_fk", "crm.Operation", "ConversationId"),
            ("operation_message_fk", "crm.Operation", "MessageId"),
        ):
            rejected(label, f"UPDATE {table} SET {column}=?", (str(uuid.uuid4()),))
        rejected(
            "conversation_unique_contact",
            """INSERT crm.Conversation
          (ConversationId,ContactId,State,Priority,ControlMode,Unread)
          VALUES(?,?,'open','normal','human',0)""",
            (str(uuid.uuid4()), contact),
        )
        rejected(
            "configuration_operation_revision",
            """INSERT crm_config.Operation
          (OperationId,PayloadHash,Revision) VALUES(?,?,1)""",
            (str(uuid.uuid4()), bytes(32)),
        )
        rejected(
            "journal_update_denied",
            "UPDATE crm_meta.MigrationJournal SET UnitId=UnitId WHERE 1=0;",
            state="42000",
        )
        rejected(
            "journal_delete_denied",
            "DELETE FROM crm_meta.MigrationJournal WHERE 1=0;",
            state="42000",
        )
        journal_probe = """INSERT crm_meta.MigrationJournal
          (AttemptId,UnitId,EventKind,ReleaseId,ToolVersion,ManifestSha256,UnitSha256,
           ShapeVersion,TargetSha256,EvidenceRef,ApprovalRef,BackupRef,PrincipalRef,
           ErrorCode,SuccessKey)
          SELECT NEWID(),?,?,ReleaseId,ToolVersion,ManifestSha256,
           UnitSha256,ShapeVersion,
           TargetSha256,EvidenceRef,ApprovalRef,BackupRef,PrincipalRef,?,?
          FROM crm_meta.MigrationJournal WHERE EventId=
           (SELECT MIN(EventId) FROM crm_meta.MigrationJournal)"""
        for label, unit, kind, error, success in (
            ("journal_event_enum", "synthetic-probe", "INVALID", None, None),
            ("journal_success_required", "synthetic-probe", "COMMITTED", None, None),
            (
                "journal_success_only_terminal",
                "synthetic-probe",
                "STARTED",
                None,
                "synthetic-probe",
            ),
            (
                "journal_success_error_null",
                "synthetic-probe",
                "COMMITTED",
                "bad",
                "synthetic-probe",
            ),
            ("journal_success_unique", "CBN-B000", "COMMITTED", None, "CBN-B000"),
        ):
            rejected(label, journal_probe, (unit, kind, error, success))
        # Permission introspection avoids academic writes even in negative tests.
        permissions = cursor.execute("""SELECT
          HAS_PERMS_BY_NAME('dbo.ACProgramas','OBJECT','ALTER'),
          HAS_PERMS_BY_NAME('dbo.ACProgramas','OBJECT','INSERT'),
          HAS_PERMS_BY_NAME('dbo.ACProgramas','OBJECT','UPDATE'),
          HAS_PERMS_BY_NAME('dbo.ACProgramas','OBJECT','DELETE'),
          HAS_PERMS_BY_NAME('dbo','SCHEMA','ALTER')""").fetchone()
        require(
            tuple(permissions) == (0, 0, 0, 0, 0), "academic_or_dbo_write_permissions"
        )
        checks.extend(["valid_enum_values", "academic_and_dbo_permissions_denied"])
    finally:
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION; SET XACT_ABORT ON;")
        cursor.close()
    return checks
