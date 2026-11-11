"""Explicit health contracts: process life does not prove integrations."""

from typing import Literal

from pydantic import BaseModel


class ProcessHealth(BaseModel):
    status: Literal["alive"] = "alive"
    mode: Literal["local_demo", "local_readonly_catalog", "local_sql_copy"] = (
        "local_demo"
    )


class IntegrationReadiness(BaseModel):
    status: Literal["not_ready"] = "not_ready"
    reason: str = "Business integrations are not configured in phase zero"
    integrations: dict[str, Literal["not_configured"]]


def integration_readiness() -> IntegrationReadiness:
    return IntegrationReadiness(
        integrations={
            name: "not_configured"
            for name in ("sql_server", "redis", "identity", "providers")
        }
    )
