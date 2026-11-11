"""Conversation analysis module public composition boundary."""


def install_analysis(application):
    from app.modules.conversation_analysis.application.runtime import (
        install_analysis as install,
    )

    return install(application)


__all__ = ["install_analysis"]
