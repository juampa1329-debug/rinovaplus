"""Capture a fresh native checkpoint while the current preview is stopped."""

import json

from tools.p3_workspace_recovery import backup
from tools.prepare_p4_channels import WORK, admin, save, source


def main():
    if (WORK / "final-checkpoint.json").exists():
        raise ValueError("P4ES_final_checkpoint_already_exists")
    settings = source()
    with admin(settings.connection["database"]) as connection:
        checkpoint = backup(connection, settings.ticket["identity"])
    save(WORK / "final-checkpoint.json", checkpoint)
    print(json.dumps({"copy_only": True, "checksum": True, "source_writes": False}))


if __name__ == "__main__":
    main()
