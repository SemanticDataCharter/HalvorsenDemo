"""
Django app configuration for despatch_advice.
"""
from django.apps import AppConfig


class Despatch_adviceConfig(AppConfig):
    """App configuration for despatch_advice."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'despatch_advice'

    def ready(self):
        """
        Import signals when app is ready.

        This ensures that signal handlers are registered when Django starts.
        """
        import despatch_advice.signals  # noqa: F401
