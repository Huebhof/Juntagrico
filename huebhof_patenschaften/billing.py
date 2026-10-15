"""Verrechnung der Patenschaften über juntagrico_billing.

Pro Patenschaft und Geschäftsjahr wird eine Rechnungsposition (BillItem mit custom_item_type) erstellt.
Hat das Mitglied im Geschäftsjahr bereits eine unveröffentlichte Rechnung (z.B. für den Ernteanteil),
kommen die Positionen dort dazu, sonst wird eine neue Rechnung erstellt.

Eingebunden wird das in die Abläufe von juntagrico_billing über views_billing.py.
"""
import datetime
from collections import defaultdict

from django.db import transaction
from django.db.models import Q

from juntagrico_billing.models.bill import Bill, BillItem, BillItemType
from juntagrico_billing.models.settings import Settings

from .models import Patenschaft

STANDARD_POSITION = 'Patenschaft'


def verrechenbar(business_year):
    """Patenschaften, die im Geschäftsjahr laufen und dafür noch nicht verrechnet sind.
    Es wird immer der volle Jahresbeitrag verrechnet."""
    return Patenschaft.objects.filter(
        aktiviert_am__isnull=False, aktiviert_am__lte=business_year.end_date, jahresbeitrag__gt=0,
    ).filter(
        Q(ende__isnull=True) | Q(ende__gte=business_year.start_date)
    ).exclude(
        rechnungspositionen__bill__business_year=business_year
    ).select_related('member', 'typ', 'typ__rechnungsposition').order_by('member__last_name', 'member__first_name',
                                                                          'typ__sortierung', 'id')


def nach_member(patenschaften):
    gruppen = defaultdict(list)
    for p in patenschaften:
        gruppen[p.member].append(p)
    return gruppen


def offene_rechnung(member, business_year):
    """Unveröffentlichte Rechnung des Mitglieds im Geschäftsjahr, an die angehängt werden kann."""
    return member.bills.filter(business_year=business_year, published=False).order_by('id').first()


def _positionstyp(typ):
    if typ.rechnungsposition_id:
        return typ.rechnungsposition
    return BillItemType.objects.get_or_create(name=STANDARD_POSITION, defaults={'booking_account': ''})[0]


def _beschreibung(typ, positionstyp):
    # Auf der Rechnung steht "<Positionstyp> <Beschreibung>", Doppelungen vermeiden.
    return '' if positionstyp.name == typ.name else typ.name[:100]


def anfuegen(bill, patenschaften):
    """Fügt die Patenschaften als Positionen an die Rechnung an und aktualisiert den Betrag."""
    for p in patenschaften:
        positionstyp = _positionstyp(p.typ)
        item = BillItem.objects.create(
            bill=bill, custom_item_type=positionstyp, description=_beschreibung(p.typ, positionstyp),
            amount=float(p.jahresbeitrag))
        p.rechnungspositionen.add(item)
    bill.amount = sum(itm.amount for itm in bill.items.all())
    bill.save()


@transaction.atomic
def verrechnen(business_year, patenschaften, bill_date=None):
    """Erstellt bzw. ergänzt die Rechnungen. Gibt (neue Rechnungen, ergänzte Rechnungen) zurück."""
    bill_date = bill_date or datetime.date.today()
    settings = Settings.objects.first()
    vat_rate = round(settings.vat_percent / 100, 4) if settings else 0.0
    neu, ergaenzt = [], []
    for member, liste in nach_member(patenschaften).items():
        bill = offene_rechnung(member, business_year)
        if bill:
            ergaenzt.append(bill)
        else:
            bill = Bill.objects.create(
                business_year=business_year, member=member, amount=0.0, vat_rate=vat_rate,
                bill_date=bill_date, booking_date=max(business_year.start_date, bill_date))
            neu.append(bill)
        anfuegen(bill, liste)
    return neu, ergaenzt
