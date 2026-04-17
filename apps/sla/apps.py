from django.apps import AppConfig


class SlaConfig(AppConfig):
    name = 'apps.sla'
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        import apps.sla.signals  # noqa: F401
