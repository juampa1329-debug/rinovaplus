"""Container readiness validates the private SQL target without HTTP secrets."""

import os
from pathlib import Path

from app.general_preview.store import load, transaction

if __name__ == "__main__":
    with transaction(load(Path(os.environ["CRM_GENERAL_PROFILE_DIR"]))):
        pass
