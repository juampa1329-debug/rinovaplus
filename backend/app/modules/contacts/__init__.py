"""Contacts module public composition boundary."""


def install_contacts(application):
    """Install contact identity, activity, and merge contracts in order."""
    from app.modules.contacts.api.router import install_institutional_identity
    from app.modules.contacts.application.activity import install_contact_activity
    from app.modules.contacts.application.merge import install_contact_merge

    install_institutional_identity(application)
    install_contact_activity(application)
    install_contact_merge(application)


__all__ = ["install_contacts"]
