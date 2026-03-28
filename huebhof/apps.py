from django.apps import AppConfig
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext as _


class HuebhofConfig(AppConfig):
    name = 'huebhof'
    verbose_name = "Huebhof"

    def ready(self):
        from juntagrico.config import Config

        def agb_label():
            documents = {
                'die Vereinbarung für einen Ernteanteil': Config.extra_sub_info,
            }
            documents_html = []
            for text, link in documents.items():
                if link().strip():
                    documents_html.append((link(), _(text)))
            if documents_html:
                joined_documents = format_html_join(
                    format_html(' {} ', _('und')),
                    '<a target="_blank" href="{}">{}</a>',
                    documents_html
                )
                return format_html(
                    _('Ich habe {} gelesen und bin mit dieser einverstanden.'),
                    joined_documents
                )
            else:
                return _('Ich erkläre meinen Willen, "{}" beizutreten. '
                         'Hiermit beantrage ich meine Aufnahme.').format(Config.organisation_long_name())

        from juntagrico.forms import RegisterMemberForm
        RegisterMemberForm.agb_label = staticmethod(agb_label)
        
