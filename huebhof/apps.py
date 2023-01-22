from django.apps import AppConfig
from django.utils.translation import gettext as _


class HuebhofConfig(AppConfig):
    name = 'huebhof'
    verbose_name = "Huebhof"

    def ready(self):
        from juntagrico.config import Config

        def agb_label():
            documents = {
                'den Abovertrag': Config.extra_sub_info,
            }
            documents_html = []
            for text, link in documents.items():
                if link().strip():
                    documents_html.append('<a target="_blank" href="{}">{}</a>'.format(link(), _(text)))
            if documents_html:
                return _('Ich habe {} gelesen und bin mit diesem einverstanden.').format(
                    (' ' + _('und') + ' ').join(documents_html),
                    Config.organisation_long_name()
                )
            else:
                return _('Ich erkläre meinen fhjhfhjfghjfjghWillen, "{}" beizutreten. '
                         'Hiermit beantrage ich meine Aufnahme.').format(Config.organisation_long_name())

        from juntagrico.forms import RegisterMemberForm
        RegisterMemberForm.agb_label = staticmethod(agb_label)
