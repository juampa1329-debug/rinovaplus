"""Prepare the private nginx configuration for the Coolify entry point."""

import os
from pathlib import Path

from app.institutional.deployment import DeploymentError, public_origin, transport_from_env


def main():
    try:
        transport = transport_from_env(os.environ)
        origin = public_origin(os.environ) if transport else None
    except DeploymentError as error:
        raise SystemExit(str(error)) from None
    config = Path("/etc/nginx/general.conf").read_text(encoding="utf-8")
    if origin:
        host = origin.removeprefix("https://")
        config = config.replace(
            '"localhost:4178" 1;', f'"localhost:4178" 1;\n        "{host}" 1;'
        )
        config = config.replace('proxy_set_header Host "127.0.0.1:8004";', "proxy_set_header Host $http_host;")
    Path("/tmp/nginx/coolify.conf").write_text(config, encoding="utf-8")


if __name__ == "__main__":
    main()
