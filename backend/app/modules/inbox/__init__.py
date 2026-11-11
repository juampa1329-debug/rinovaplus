"""Inbox module public composition boundary."""

from app.modules.inbox.api.router import install_inbox, install_inbox_operations

__all__ = ["install_inbox", "install_inbox_operations"]
