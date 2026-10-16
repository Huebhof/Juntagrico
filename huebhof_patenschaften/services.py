import datetime

from django.db import transaction

from .config import SponsorshipConfig
from .models import Sponsorship, SponsorshipType


def resolve_selection(selection):
    """{'type_id': quantity} (from session/form) -> [(SponsorshipType, quantity)] with quantity > 0."""
    selection = {str(k): int(v or 0) for k, v in (selection or {}).items()}
    types = SponsorshipType.objects.filter(id__in=[k for k, v in selection.items() if v > 0])
    return [(sponsorship_type, selection[str(sponsorship_type.id)]) for sponsorship_type in types]


@transaction.atomic
def order(member, selection, date=None):
    """Creates one sponsorship per ordered unit and returns the new objects."""
    date = date or datetime.date.today()
    activation_date = date if SponsorshipConfig.auto_activate() else None
    created = []
    for sponsorship_type, quantity in resolve_selection(selection):
        for _ in range(quantity):
            created.append(Sponsorship.objects.create(
                member=member, type=sponsorship_type, annual_fee=sponsorship_type.annual_fee,
                order_date=date, activation_date=activation_date,
            ))
    return created


@transaction.atomic
def create(member, sponsorship_type, quantity, annual_fee=None, order_date=None, activation_date=None, notes=''):
    """Created by admins: dates are given explicitly, SPONSORSHIPS_AUTO_ACTIVATE does not apply."""
    return [Sponsorship.objects.create(
        member=member, type=sponsorship_type,
        annual_fee=sponsorship_type.annual_fee if annual_fee is None else annual_fee,
        order_date=order_date or datetime.date.today(), activation_date=activation_date, notes=notes,
    ) for _ in range(quantity)]


def group(sponsorships):
    """Groups sponsorships by type and status for display ("3 × tree sponsorship")."""
    groups = {}
    for s in sponsorships:
        key = (s.type_id, s.status, s.end_date)
        if key not in groups:
            groups[key] = {'type': s.type, 'status': s.status, 'status_display': s.get_status_display(),
                           'end_date': s.end_date, 'objects': [], 'total': 0}
        groups[key]['objects'].append(s)
        groups[key]['total'] += s.annual_fee
    for g in groups.values():
        g['quantity'] = len(g['objects'])
    return list(groups.values())
