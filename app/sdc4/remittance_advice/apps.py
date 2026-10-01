"""
Django app configuration for remittance_advice.
"""
from django.apps import AppConfig


class Remittance_adviceConfig(AppConfig):
    """App configuration for remittance_advice."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'remittance_advice'

    def ready(self):
        """
        Import signals when app is ready.

        This ensures that signal handlers are registered when Django starts.
        """
        import remittance_advice.signals  # noqa: F401
