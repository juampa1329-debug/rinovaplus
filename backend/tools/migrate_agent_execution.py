"""Apply only the explicit local execution ledger; no startup DDL or transport."""

import argparse
from pathlib import Path

import pyodbc

from app.config import Settings
from app.environment import load_environment
from app.sql_workspace import connection_string, verify_target


def verify_shape(cursor):
    expected = {
        "RequestId": ("uniqueidentifier", 16, False), "AgentId": ("uniqueidentifier", 16, False),
        "AgentVersion": ("bigint", 8, False), "ConversationId": ("uniqueidentifier", 16, True),
        "Provider": ("varchar", 30, False), "ModelId": ("nvarchar", 400, False),
        "Route": ("varchar", 30, False), "Variant": ("nvarchar", 80, False),
        "FallbackUsed": ("bit", 1, False), "PricingJson": ("nvarchar", -1, False),
        "AttemptsJson": ("nvarchar", -1, False), "CostReserved": ("decimal", 13, True),
        "CostEstimated": ("decimal", 13, True), "InputTokens": ("bigint", 8, True),
        "OutputTokens": ("bigint", 8, True), "LatencyMs": ("bigint", 8, True),
        "State": ("varchar", 12, False), "ErrorCode": ("varchar", 80, True),
        "SourceFingerprint": ("varchar", 64, False), "CreatedAt": ("datetime2", 8, False),
        "FinishedAt": ("datetime2", 8, True),
    }
    rows = cursor.execute("SELECT c.name,t.name,c.max_length,c.is_nullable,c.precision,c.scale FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE c.object_id=OBJECT_ID(N'crm_agents.Execution')").fetchall()
    actual = {r[0]: (r[1], r[2], bool(r[3])) for r in rows}
    if actual != expected or any(r[1] == "decimal" and (r[4], r[5]) != (20, 8) for r in rows):
        raise SystemExit("agents_execution_shape_unrecognized")
    if cursor.execute("SELECT COUNT(*) FROM sys.foreign_keys WHERE parent_object_id=OBJECT_ID(N'crm_agents.Execution') AND referenced_object_id IN(OBJECT_ID(N'crm_agents.Usage'),OBJECT_ID(N'crm_agents.Profile'),OBJECT_ID(N'crm.Conversation'))").fetchval() != 3:
        raise SystemExit("agents_execution_shape_unrecognized")
    if cursor.execute("SELECT COUNT(*) FROM sys.indexes WHERE object_id=OBJECT_ID(N'crm_agents.Execution') AND name IN('IX_AgentExecution_AgentCreated','IX_AgentExecution_Conversation')").fetchval() != 2:
        raise SystemExit("agents_execution_shape_unrecognized")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    options = parser.parse_args()
    load_environment()
    settings = Settings.from_environment()
    if settings.mode != "local_sql_copy":
        raise SystemExit("local_sql_copy_required")
    connection = pyodbc.connect(connection_string(settings), timeout=5, autocommit=False)
    try:
        connection.timeout = 30
        cursor = connection.cursor()
        cursor.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000;")
        verify_target(cursor, settings)
        cursor.execute("DECLARE @lock int; EXEC @lock=sys.sp_getapplock @Resource=N'crm.local.commit',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=5000; IF @lock<0 THROW 51004,'Migration lock unavailable.',1;")
        if cursor.execute("SELECT OBJECT_ID(N'crm_agents.Usage')").fetchval() is None:
            raise SystemExit("agents_migration_required")
        exists = cursor.execute("SELECT OBJECT_ID(N'crm_agents.Execution')").fetchval() is not None
        contract = cursor.execute("SELECT CONVERT(nvarchar(80),value) FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_agents') AND name=N'crm_agents.execution_contract'").fetchval()
        if exists:
            if contract != "agent-execution-v1":
                raise SystemExit("agents_execution_shape_unrecognized")
            verify_shape(cursor)
        elif contract:
            raise SystemExit("agents_execution_shape_unrecognized")
        if options.preflight or exists:
            connection.rollback()
            print("Verified local target; execution ledger " + ("already installed; no changes." if exists else "not installed; preflight only."))
            return
        cursor.execute(Path(__file__).resolve().parents[1].joinpath("migrations", "020_agent_execution.sql").read_text(encoding="utf-8"))
        while cursor.nextset():
            pass
        verify_target(cursor, settings)
        verify_shape(cursor)
        connection.commit()
        print("Agent-execution-v1 applied to verified local copy; no transport enabled.")
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
