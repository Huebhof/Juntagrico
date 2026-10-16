from django.conf import settings


class SponsorshipConfig:
    """Settings of the addon. All values can be overridden in settings.py."""

    @staticmethod
    def auto_activate():
        """False (default, like subscriptions): admins activate orders manually.
        True: sponsorships are active from the order date."""
        return getattr(settings, 'SPONSORSHIPS_AUTO_ACTIVATE', False)

    @staticmethod
    def in_signup():
        """True: show a sponsorship step in the signup / subscription order process."""
        return getattr(settings, 'SPONSORSHIPS_IN_SIGNUP', True)

    @staticmethod
    def max_quantity():
        """Maximum quantity per type and order."""
        return getattr(settings, 'SPONSORSHIPS_MAX_QUANTITY', 20)

    @staticmethod
    def info_url():
        """Optional link to a document with information about the sponsorships."""
        return getattr(settings, 'SPONSORSHIPS_INFO_URL', '')
