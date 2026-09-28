"""
Django app configuration for order_response.
"""
from django.apps import AppConfig


class Order_responseConfig(AppConfig):
    """App configuration for order_response."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'order_response'

    def ready(self):
        """
        Import signals when app is ready.

        This ensures that signal handlers are registered when Django starts.
        """
        import order_response.signals  # noqa: F401
