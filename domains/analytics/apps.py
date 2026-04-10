from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'domains.analytics'
    label = 'analytics'

    def ready(self):
        """Conecta analytics a los eventos de help_desk al arrancar Django."""
        from shared.events import domain_event_signal
        from .services import create_snapshot_from_event

        def on_domain_event(sender, event, **kwargs):
            if event.event_type.startswith('help_desk.'):
                try:
                    create_snapshot_from_event(event)
                except Exception:
                    pass  # analytics nunca debe romper el flujo operativo

        domain_event_signal.connect(on_domain_event)
