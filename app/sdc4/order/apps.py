"""
Django app configuration for order.
"""
from django.apps import AppConfig


class OrderConfig(AppConfig):
    """App configuration for order."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'order'

    def ready(self):
        """
        Import signals when app is ready.

        This ensures that signal handlers are registered when Django starts.
        """
        import order.signals  # noqa: F401
