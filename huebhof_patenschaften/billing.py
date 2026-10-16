"""Billing of sponsorships via juntagrico_billing.

One bill item (BillItem with custom_item_type) is created per sponsorship and business year.
If the member already has an unpublished bill in the business year (e.g. for the subscription),
the items are added to it, otherwise a new bill is created.

Hooked into the juntagrico_billing workflow via views_billing.py.
"""
import datetime
from collections import defaultdict

from django.db import transaction
from django.db.models import Q

from juntagrico_billing.models.bill import Bill, BillItem, BillItemType
from juntagrico_billing.models.settings import Settings

from .models import Sponsorship

DEFAULT_ITEM_TYPE = 'Patenschaft'


def billable(business_year):
    """Sponsorships running in the business year that are not billed for it yet.
    The full annual fee is always billed."""
    return Sponsorship.objects.filter(
        activation_date__isnull=False, activation_date__lte=business_year.end_date, annual_fee__gt=0,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=business_year.start_date)
    ).exclude(
        bill_items__bill__business_year=business_year
    ).select_related('member', 'type', 'type__bill_item_type').order_by('member__last_name', 'member__first_name',
                                                                        'type__sort_order', 'id')


def by_member(sponsorships):
    groups = defaultdict(list)
    for s in sponsorships:
        groups[s.member].append(s)
    return groups


def open_bill(member, business_year):
    """Unpublished bill of the member in the business year that items can be added to."""
    return member.bills.filter(business_year=business_year, published=False).order_by('id').first()


def _item_type(sponsorship_type):
    if sponsorship_type.bill_item_type_id:
        return sponsorship_type.bill_item_type
    return BillItemType.objects.get_or_create(name=DEFAULT_ITEM_TYPE, defaults={'booking_account': ''})[0]


def _description(sponsorship_type, item_type):
    # The bill shows "<item type> <description>", avoid duplicates.
    return '' if item_type.name == sponsorship_type.name else sponsorship_type.name[:100]


def add_to_bill(bill, sponsorships):
    """Adds the sponsorships as items to the bill and updates the amount."""
    for s in sponsorships:
        item_type = _item_type(s.type)
        item = BillItem.objects.create(
            bill=bill, custom_item_type=item_type, description=_description(s.type, item_type),
            amount=float(s.annual_fee))
        s.bill_items.add(item)
    bill.amount = sum(itm.amount for itm in bill.items.all())
    bill.save()


@transaction.atomic
def create_bills(business_year, sponsorships, bill_date=None):
    """Creates or extends the bills. Returns (new bills, extended bills)."""
    bill_date = bill_date or datetime.date.today()
    settings = Settings.objects.first()
    vat_rate = round(settings.vat_percent / 100, 4) if settings else 0.0
    created, extended = [], []
    for member, member_sponsorships in by_member(sponsorships).items():
        bill = open_bill(member, business_year)
        if bill:
            extended.append(bill)
        else:
            bill = Bill.objects.create(
                business_year=business_year, member=member, amount=0.0, vat_rate=vat_rate,
                bill_date=bill_date, booking_date=max(business_year.start_date, bill_date))
            created.append(bill)
        add_to_bill(bill, member_sponsorships)
    return created, extended
