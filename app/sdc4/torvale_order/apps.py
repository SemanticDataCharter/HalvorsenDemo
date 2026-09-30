"""
Django app configuration for torvale_order.
"""
from django.apps import AppConfig


class Torvale_orderConfig(AppConfig):
    """App configuration for torvale_order."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'torvale_order'

    def ready(self):
        """
        Import signals when app is ready.

        This ensures that signal handlers are registered when Django starts.
        """
        import torvale_order.signals  # noqa: F401
