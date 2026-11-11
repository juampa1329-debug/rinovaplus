"""Public UI capabilities describe composition, never SQL readiness or credentials."""

from fastapi.responses import JSONResponse

FEATURES = (
    "academic",
    "advancedCrm",
    "inboxOperations",
    "assessment",
    "media",
    "externalDelivery",
    "automation",
    "comments",
    "readSequence",
    "providers",
)


def manifest(settings):
    foundation = settings.mode == "local_foundation"
    return {
        "version": "cbn-ui-capabilities-v1",
        "profile": "foundation" if foundation else "legacy",
        "mode": settings.mode,
        "modules": ["overview", "clients", "inbox", "settings"] if foundation else None,
        "features": {key: not foundation for key in FEATURES},
        "scope": "restored_rehearsal_only"
        if foundation
        else "existing_local_composition",
    }


def install_runtime_capabilities(application):
    @application.get("/api/local/runtime")
    def runtime():
        return JSONResponse(
            manifest(application.state.settings), headers={"Cache-Control": "no-store"}
        )
