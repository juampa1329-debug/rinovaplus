"""AI module public composition boundary."""


def install_ai(application, ai_service=None):
    """Install AI routes without importing the module during bridge loading."""
    from app.modules.ai.api.router import install_ai as install

    return install(application, ai_service)


__all__ = ["install_ai"]
