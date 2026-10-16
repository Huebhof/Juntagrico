from django.apps import AppConfig


class HuebhofPatenschaftenBillingConfig(AppConfig):
    name = 'huebhof_patenschaften_billing'
    verbose_name = 'Patenschaften: Verrechnung'
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        from huebhof_patenschaften.extensions import register_type_form_extension
        from .forms import BillItemTypeFormExtension
        register_type_form_extension(BillItemTypeFormExtension())
