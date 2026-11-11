"""Load only this checkout's private environment without expanding secret values."""

from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def load_environment() -> None:
    try:
        load_dotenv(
            dotenv_path=ENV_FILE,
            override=False,
            interpolate=False,
            encoding="utf-8-sig",
        )
    except (OSError, UnicodeError):
        raise ValueError(
            "Local environment configuration could not be loaded"
        ) from None
