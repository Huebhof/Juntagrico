from django.apps import AppConfig


class HuebhofPatenschaftenConfig(AppConfig):
    name = 'huebhof_patenschaften'
    verbose_name = 'Patenschaften'
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        from . import receivers  # noqa: F401
