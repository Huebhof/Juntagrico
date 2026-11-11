from juntagrico.password_validation import StaffOnlyPasswordValidator


class PrivilegedOnlyPasswordValidator(StaffOnlyPasswordValidator):
    """
    Wie juntagrico.password_validation.PrivilegedOnlyPasswordValidator:
    Passwortprüfung für Admins, Mitarbeitende, Konten mit Berechtigungen oder
    Gruppen sowie Koordinator:innen von Tätigkeitsbereichen und Depots.

    Ersetzt die Juntagrico-Variante (2.0.11), die auf das nicht existierende
    ``user.permissions`` zugreift und dadurch bei jedem nicht privilegierten
    Konto (z. B. beim Login) mit einem AttributeError abbricht.
    """

    def filter(self, user):
        if super().filter(user):
            return True
        if user.pk is None:
            # neues, noch nicht gespeichertes Konto (Anmeldung): keine Rechte
            return False
        if user.user_permissions.exists() or user.groups.exists():
            return True
        member = getattr(user, 'member', None)
        return member is not None and (
            member.coordinated_areas.exists() or member.coordinated_depots.exists()
        )
