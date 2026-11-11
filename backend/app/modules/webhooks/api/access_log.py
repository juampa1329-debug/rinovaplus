"""Remove verification queries from Uvicorn's application access records."""

import logging


class VerificationQueryFilter(logging.Filter):
    def filter(self, record):
        # Uvicorn's access record uses (client, method, full_path, version, status).
        if isinstance(record.args, tuple) and len(record.args) == 5:
            path = record.args[2]
            if isinstance(path, str) and path.split("?", 1)[0].rstrip("/").endswith(
                "/api/v1/webhooks/meta"
            ):
                record.args = (
                    *record.args[:2],
                    path.split("?", 1)[0],
                    *record.args[3:],
                )
        return True


def install_query_filter():
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, VerificationQueryFilter) for item in logger.filters):
        logger.addFilter(VerificationQueryFilter())
