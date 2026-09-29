"""
Django app configuration for receipt_advice.
"""
from django.apps import AppConfig


class Receipt_adviceConfig(AppConfig):
    """App configuration for receipt_advice."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'receipt_advice'

    def ready(self):
        """
        Import signals when app is ready.

        This ensures that signal handlers are registered when Django starts.
        """
        import receipt_advice.signals  # noqa: F401
