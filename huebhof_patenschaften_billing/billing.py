"""Billing of sponsorships via juntagrico_billing.

One bill item (BillItem with custom_item_type) is created per sponsorship and business year.
Unlike subscriptions in juntagrico_billing, the full annual fee is billed for every business year
the sponsorship runs in, also if it starts or ends during the year (no pro rata).
If the member already has an unpublished bill in the business year (e.g. for the subscription),
the items are added to it, otherwise a new bill is created.

Hooked into the juntagrico_billing workflow via views.py.
"""
import datetime
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum

from juntagrico_billing.models.bill import Bill, BillItem, BillItemType, BusinessYear
from juntagrico_billing.models.settings import Settings

from huebhof_patenschaften.models import Sponsorship

from .models import SponsorshipBillItem, bill_item_type_of

DEFAULT_ITEM_TYPE = 'Patenschaft'


def billable(business_year):
    """Sponsorships running in the business year that are not billed for it yet."""
    return Sponsorship.objects.with_fee().filter(
        activation_date__isnull=False, activation_date__lte=business_year.end_date, fee__gt=0,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=business_year.start_date)
    ).exclude(
        bill_item_links__bill_item__bill__business_year=business_year
    ).select_related('member', 'type', 'type__billing__bill_item_type').order_by(
        'member__last_name', 'member__first_name', 'type__sort_order', 'id')


def by_member(sponsorships):
    groups = defaultdict(list)
    for s in sponsorships:
        groups[s.member].append(s)
    return groups


def open_bill(member, business_year):
    """Unpublished bill of the member in the business year that items can be added to."""
    return member.bills.filter(business_year=business_year, published=False).order_by('id').first()


def _item_type(sponsorship_type):
    item_type = bill_item_type_of(sponsorship_type)
    if item_type:
        return item_type
    return BillItemType.objects.get_or_create(name=DEFAULT_ITEM_TYPE, defaults={'booking_account': ''})[0]


def amount(sponsorship, business_year):
    """Amount billed for the sponsorship in the business year: always the full annual fee."""
    return sponsorship.annual_fee


def _description(sponsorship, item_type):
    # The bill shows "<item type> <description>", avoid duplicates.
    return '' if item_type.name == sponsorship.type.name else sponsorship.type.name[:100]


def _update_total(bill):
    bill.amount = sum(itm.amount for itm in bill.items.all())
    bill.save()


def add_to_bill(bill, sponsorships):
    """Adds the sponsorships as items to the bill and updates the amount."""
    for s in sponsorships:
        item_type = _item_type(s.type)
        item = BillItem.objects.create(
            bill=bill, custom_item_type=item_type, description=_description(s, item_type),
            amount=float(amount(s, bill.business_year)))
        SponsorshipBillItem.objects.create(sponsorship=s, bill_item=item)
    _update_total(bill)


def recalc(bill):
    """Updates the sponsorship items of the bill (e.g. after a price change)
    and adds missing sponsorships of the member."""
    for link in SponsorshipBillItem.objects.filter(bill_item__bill=bill).select_related(
            'bill_item__custom_item_type', 'sponsorship__type'):
        item = link.bill_item
        item.amount = float(amount(link.sponsorship, bill.business_year))
        item.description = _description(link.sponsorship, item.custom_item_type)
        item.save()
    add_to_bill(bill, billable(bill.business_year).filter(member=bill.member))


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


def billed_per_type(date=None):
    """Billed amounts of the business year containing the date (default: today), also of unpublished bills.
    None if there is no such business year in juntagrico_billing."""
    date = date or datetime.date.today()
    business_year = BusinessYear.objects.filter(start_date__lte=date, end_date__gte=date).first()
    if business_year is None:
        return None
    rows = SponsorshipBillItem.objects.filter(bill_item__bill__business_year=business_year).values(
        'sponsorship__type').annotate(amount=Sum('bill_item__amount'))
    per_type = {row['sponsorship__type']: Decimal(str(round(row['amount'], 2))) for row in rows}
    return {
        'year': business_year.name or business_year.start_date.year,
        'per_type': per_type,
        'total': sum(per_type.values(), Decimal('0')),
    }
