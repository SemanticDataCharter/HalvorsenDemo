"""
Django app configuration for credit_note.
"""
from django.apps import AppConfig


class Credit_noteConfig(AppConfig):
    """App configuration for credit_note."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'credit_note'

    def ready(self):
        """
        Import signals when app is ready.

        This ensures that signal handlers are registered when Django starts.
        """
        import credit_note.signals  # noqa: F401
