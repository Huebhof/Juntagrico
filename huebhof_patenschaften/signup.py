from juntagrico.util.sessions import SignupManager

from . import mailer, services
from .config import PatenschaftConfig
from .models import PatenschaftTyp

# Schritte, die vor der Patenschaften-Seite kommen (Auswahl der Ernteanteile und Zusatz-Abos)
_VORHERIGE_SCHRITTE = ('signup', 'subscription-landing', 'cs-subscription', 'cs-extras')


class PatenschaftSignupManager(SignupManager):
    """Erweitert den Bestellprozess um einen Schritt "Patenschaften" nach der Auswahl der Ernteanteile.

    Aktivieren in settings.py:
        SIGNUP_MANAGER = 'huebhof_patenschaften.signup.PatenschaftSignupManager'
    """

    def patenschaften_enabled(self):
        return PatenschaftConfig.im_signup() and PatenschaftTyp.objects.sichtbar().exists()

    def patenschaften(self):
        """[(PatenschaftTyp, anzahl)] der gewählten Patenschaften."""
        return services.auswahl_aufloesen(self.get('patenschaften', {}))

    def get_next_page(self):
        next_page = super().get_next_page()
        url_name = self.request.resolver_match.url_name
        if self.request.GET.get('mod') is not None or url_name == 'cs-cancel':
            return next_page  # bei "?mod" bleibt die Seite, die bearbeitet wird
        if next_page in _VORHERIGE_SCHRITTE:
            return next_page
        if self.patenschaften_enabled() and self.get('patenschaften') is None:
            return 'cs-patenschaften'
        return next_page

    def apply_subscriptions(self, member, co_members):
        subscription = super().apply_subscriptions(member, co_members)
        self._neue_patenschaften = services.bestellen(member.member, self.get('patenschaften', {}))
        return subscription

    def send_emails(self, member, co_members, subscription):
        super().send_emails(member, co_members, subscription)
        neue = getattr(self, '_neue_patenschaften', [])
        if neue:
            mailer.bestaetigung_an_pate(member.member, neue)
            mailer.admin_bestellt(member.member, neue)
