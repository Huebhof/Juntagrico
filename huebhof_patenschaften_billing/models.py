from django.db import models
from django.utils.translation import gettext_lazy as _

from juntagrico_billing.models.bill import BillItem, BillItemType

from huebhof_patenschaften.models import Sponsorship, SponsorshipType


class SponsorshipTypeBilling(models.Model):
    """Billing settings of a sponsorship type."""
    type = models.OneToOneField(
        SponsorshipType, on_delete=models.CASCADE, primary_key=True, related_name='billing',
        verbose_name=_('Patenschaftstyp'))
    bill_item_type = models.ForeignKey(
        BillItemType, verbose_name=_('Rechnungspositionstyp'),
        null=True, blank=True, on_delete=models.PROTECT, related_name='sponsorship_types',
        help_text=_('Bestimmt das Buchungskonto auf der Rechnung. Leer: Rechnungspositionstyp "Patenschaft".'))

    class Meta:
        verbose_name = _('Verrechnung')
        verbose_name_plural = _('Verrechnung')

    def __str__(self):
        return str(self.bill_item_type or '')


class SponsorshipBillItem(models.Model):
    """Bill item with which a sponsorship was billed for a business year."""
    sponsorship = models.ForeignKey(
        Sponsorship, on_delete=models.CASCADE, related_name='bill_item_links', verbose_name=_('Patenschaft'))
    bill_item = models.OneToOneField(
        BillItem, on_delete=models.CASCADE, related_name='sponsorship_link', verbose_name=_('Rechnungsposition'))

    class Meta:
        verbose_name = _('Rechnung')
        verbose_name_plural = _('Rechnungen')
        ordering = ['bill_item__bill__business_year__start_date']

    def __str__(self):
        return f'{self.bill_item.bill_id} ({self.bill_item.bill.business_year})'


def bill_item_type_of(sponsorship_type):
    """Bill item type configured for the sponsorship type, or None."""
    billing = getattr(sponsorship_type, 'billing', None)
    return billing.bill_item_type if billing else None
