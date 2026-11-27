"""Keep the integrated unit suite isolated from operator state and real IO."""

import os
import socket
from pathlib import Path

import pytest

# Collection and unit tests must never load the checkout's private .env file.
# Environment-loader tests opt in only after replacing its path with a fixture.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"

# Older host python-dotenv versions ignore that switch. Redirect the path before
# app collection as well; loader tests explicitly replace it with a temp file.
from app import environment  # noqa: E402

environment.ENV_FILE = Path(__file__).parent / "_disabled_operator_env" / ".env"
assert not environment.ENV_FILE.exists()

# Collection constructs the app before fixtures run. Never inherit enabled
# provider output, a SQL mode or secrets from the developer's process.
for variable in (
    "CRM_APP_MODE",
    "CRM_CATALOG_TOKEN",
    "CRM_META_VERIFY_TOKEN_SHA256",
    "CRM_SQL_USER",
    "CRM_SQL_PASSWORD",
    "CRM_SQL_SERVER",
    "CRM_SQL_DATABASE",
    "CRM_SQL_HOST",
    "CRM_SQL_PORT",
    "CRM_SQL_ENVIRONMENT",
    "CRM_SQL_EXPECTED_MACHINE",
    "CRM_SQL_CERTIFICATE_HOSTNAME",
    "CRM_SQL_EXPECTED_SERVER",
    "CRM_SQL_EXPECTED_INSTANCE",
    "CRM_SQL_EXPECTED_LOGIN",
    "CRM_SQL_EXPECTED_DATABASE_USER",
    "CRM_FOUNDATION_TICKET_PATH",
    "CRM_FOUNDATION_PROFILE_DIR",
    "CRM_FOUNDATION_TICKET_SHA256",
    "CRM_CHANNELS_PROFILE_DIR",
    "CRM_CHANNELS_UI_PROFILE_DIR",
    "CRM_CATALOG_ORIGINS",
    "CRM_AI_OUTBOUND_ENABLED",
    "CRM_AI_STATE_DIR",
    "SIIE_BASE_URL",
    "SIIE_API_BASE_URL",
    "SIIE_API_TOKEN",
    "SIIE_CATALOG_API_TOKEN",
    "GEMINI_API_KEY",
    "XAI_API_KEY",
    "OPENROUTER_API_KEY",
    "ELEVENLABS_API_KEY",
    "GOOGLE_TTS_API_KEY",
    "TAVILY_API_KEY",
    "BRAVE_API_KEY",
    "BRAVE_SEARCH_API_KEY",
    "SERPAPI_API_KEY",
):
    os.environ.pop(variable, None)


@pytest.fixture(autouse=True)
def isolated_integrations(monkeypatch, tmp_path_factory):
    import pyodbc

    from app.modules.ai.application.service import SettingsRepository
    from app.modules.ai.infrastructure.credentials import CredentialRepository

    def forbidden(*args, **kwargs):
        pytest.fail("Real outbound IO is forbidden in the integrated unit suite")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(pyodbc, "connect", forbidden)
    protected = Path(__file__).resolve().parents[2] / ".local"
    synthetic = tmp_path_factory.getbasetemp().resolve()
    for repository in (SettingsRepository, CredentialRepository):
        original = repository.read

        def safe_read(self, read=original):
            location = self.path.resolve()
            assert not location.is_relative_to(protected) or location.is_relative_to(
                synthetic
            ), "Operator state must not be loaded by unit tests"
            return read(self)

        monkeypatch.setattr(repository, "read", safe_read)
