"""Conversation events module public composition boundary."""


def install_events(application):
    from app.modules.conversation_events.api.router import install_events as install

    return install(application)


__all__ = ["install_events"]
