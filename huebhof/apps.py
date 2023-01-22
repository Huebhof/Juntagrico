from django.apps import AppConfig
from django.utils.translation import gettext as _
​
​
class HuebhofConfig(AppConfig):
    name = 'huebhof'
    verbose_name = "Huebhof"
​
    def ready(self):
        from juntagrico.config import Config