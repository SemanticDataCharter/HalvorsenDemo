"""
Django app configuration for invoice.
"""
from django.apps import AppConfig


class InvoiceConfig(AppConfig):
    """App configuration for invoice."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'invoice'

    def ready(self):
        """
        Import signals when app is ready.

        This ensures that signal handlers are registered when Django starts.
        """
        import invoice.signals  # noqa: F401
