from juntagrico.util.sessions import SignupManager

from . import mailer, services
from .config import SponsorshipConfig
from .models import SponsorshipType

# Steps that come before the sponsorship page (selection of subscriptions and extras)
_PREVIOUS_STEPS = ('signup', 'subscription-landing', 'cs-subscription', 'cs-extras')


class SponsorshipSignupManager(SignupManager):
    """Extends the order process with a "sponsorships" step after the subscription selection.

    Enable in settings.py:
        SIGNUP_MANAGER = 'huebhof_patenschaften.signup.SponsorshipSignupManager'
    """

    def sponsorships_enabled(self):
        return SponsorshipConfig.in_signup() and SponsorshipType.objects.visible().exists()

    def sponsorships(self):
        """[(SponsorshipType, quantity)] of the selected sponsorships."""
        return services.resolve_selection(self.get('sponsorships', {}))

    def get_next_page(self):
        next_page = super().get_next_page()
        url_name = self.request.resolver_match.url_name
        if self.request.GET.get('mod') is not None or url_name == 'cs-cancel':
            return next_page  # with "?mod" the page being edited stays
        if next_page in _PREVIOUS_STEPS:
            return next_page
        if self.sponsorships_enabled() and self.get('sponsorships') is None:
            return 'cs-sponsorships'
        return next_page

    def apply_subscriptions(self, member, co_members):
        subscription = super().apply_subscriptions(member, co_members)
        self._new_sponsorships = services.order(member.member, self.get('sponsorships', {}))
        return subscription

    def send_emails(self, member, co_members, subscription):
        super().send_emails(member, co_members, subscription)
        created = getattr(self, '_new_sponsorships', [])
        if created:
            mailer.confirm_order(member.member, created)
            mailer.notify_admins_ordered(member.member, created)
