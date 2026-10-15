from django.conf import settings


class PatenschaftConfig:
    """Einstellungen des Addons. Alle Werte können in settings.py überschrieben werden."""

    @staticmethod
    def auto_aktivieren():
        """True: Patenschaften sind ab Bestellung aktiv. False: Admins aktivieren sie manuell."""
        return getattr(settings, 'PATENSCHAFTEN_AUTO_AKTIVIEREN', True)

    @staticmethod
    def im_signup():
        """True: Bei der Anmeldung / Ernteanteil-Bestellung wird ein Schritt Patenschaften angezeigt."""
        return getattr(settings, 'PATENSCHAFTEN_IM_SIGNUP', True)

    @staticmethod
    def max_anzahl():
        """Maximale Anzahl pro Typ und Bestellung."""
        return getattr(settings, 'PATENSCHAFTEN_MAX_ANZAHL', 20)

    @staticmethod
    def info_url():
        """Optionaler Link auf ein Dokument mit Infos zu den Patenschaften."""
        return getattr(settings, 'PATENSCHAFTEN_INFO_URL', '')
