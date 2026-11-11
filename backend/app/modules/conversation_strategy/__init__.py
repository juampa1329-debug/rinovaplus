"""Conversation strategy module public composition boundary."""


def install_strategy(application):
    from app.modules.conversation_strategy.application.runtime import (
        install_strategy as install,
    )

    return install(application)


__all__ = ["install_strategy"]
