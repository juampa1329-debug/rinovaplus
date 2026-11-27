"""Safe field names for academic editor validation, never submitted values."""


def fields(errors):
    from app.institutional.agents_api import ProgramWrite
    from app.institutional.program_commercial import (
        CommercialProfile, FinancialInstallment, FinancialPlan,
    )
    allowed = {key for model in (ProgramWrite, CommercialProfile, FinancialPlan, FinancialInstallment)
               for key in model.model_fields}
    result = []
    for error in errors[:8]:
        path = []
        for part in error.get("loc", ()):
            if part == "body" or isinstance(part, int):
                continue
            if not isinstance(part, str) or part not in allowed:
                break
            path.append(part)
        if path:
            result.append(".".join(path))
    return list(dict.fromkeys(result))


def response(path, method, errors):
    import re
    if method not in {"POST", "PUT"} or not re.fullmatch(r"/api/v1/agents/programs(?:/[1-9][0-9]*)?", path):
        return {"detail": "invalid_request"}
    return {"code": "invalid_request", "detail": "invalid_request", "fields": fields(errors)}
