from django.dispatch import receiver

from juntagrico.entity.member import Member
from juntagrico.signals import member_deactivated

from .models import Sponsorship


@receiver(member_deactivated, sender=Member)
def end_sponsorships(sender, instance, **kwargs):
    """When a member is deactivated (leaves), their sponsorships end as well."""
    date = instance.deactivation_date
    if date is None:
        return
    for s in Sponsorship.objects.filter(member=instance).open():
        if s.activation_date is None or s.activation_date > date:
            s.cancellation_date = s.cancellation_date or date
            s.activation_date = None
            s.end_date = date
        else:
            s.cancellation_date = s.cancellation_date or date
            if s.end_date is None or s.end_date > date:
                s.end_date = date
        s.save()
