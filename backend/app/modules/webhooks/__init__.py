"""Webhook verification public composition boundary."""


def install_webhooks(application):
    from app.modules.webhooks.api.access_log import install_query_filter
    from app.modules.webhooks.api.router import router

    install_query_filter()
    application.include_router(router)


__all__ = ["install_webhooks"]
