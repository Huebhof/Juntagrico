from django.dispatch import receiver

from juntagrico.entity.member import Member
from juntagrico.signals import member_deactivated

from .models import Patenschaft


@receiver(member_deactivated, sender=Member)
def patenschaften_beenden(sender, instance, **kwargs):
    """Wird ein Mitglied deaktiviert (Austritt), enden auch seine Patenschaften."""
    date = instance.deactivation_date
    if date is None:
        return
    for p in Patenschaft.objects.filter(member=instance).offen():
        if p.aktiviert_am is None or p.aktiviert_am > date:
            p.gekuendigt_am = p.gekuendigt_am or date
            p.aktiviert_am = None
            p.ende = date
        else:
            p.gekuendigt_am = p.gekuendigt_am or date
            if p.ende is None or p.ende > date:
                p.ende = date
        p.save()
