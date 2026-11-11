"""Apply the explicit AI schema and import non-secret settings once, without copies."""

import os
from pathlib import Path

import pyodbc

from app.config import Settings
from app.environment import load_environment
from app.modules.ai.domain.models import AiSettings, SaveSettings
from app.sql_workspace import connection_string, verify_target


def main():
    load_environment()
    settings = Settings.from_environment()
    if settings.mode != "local_sql_copy":
        raise SystemExit("local_sql_copy_required")
    state_path = (
        Path(os.environ.get("CRM_AI_STATE_DIR", "/var/lib/crm-ai")) / "ai-settings.json"
    )
    if state_path.exists():
        if state_path.stat().st_size > 64000:
            raise SystemExit("settings_document_too_large")
        imported = SaveSettings.model_validate_json(
            state_path.read_text(encoding="utf-8")
        )
    else:
        imported = SaveSettings(revision=0, settings=AiSettings())
    connection = pyodbc.connect(
        connection_string(settings), timeout=5, autocommit=False
    )
    try:
        connection.timeout = 15
        cursor = connection.cursor()
        cursor.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000;")
        verify_target(cursor, settings)
        cursor.execute(
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("migrations/013_ai_providers.sql")
            .read_text(encoding="utf-8")
        )
        while cursor.nextset():
            pass
        cursor.execute(
            "IF NOT EXISTS(SELECT 1 FROM crm_ai.Configuration WITH(UPDLOCK,HOLDLOCK) WHERE ConfigurationId=1) INSERT crm_ai.Configuration(ConfigurationId,Revision,Document) VALUES(1,?,?)",
            imported.revision,
            imported.settings.model_dump_json(),
        )
        connection.commit()
        print(
            "CRM-ai-v1 applied; existing settings imported once, outbound defaults OFF, no credentials exported."
        )
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
