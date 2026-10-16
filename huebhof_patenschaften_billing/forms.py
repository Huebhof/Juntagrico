from django import forms
from django.utils.translation import gettext_lazy as _

from juntagrico_billing.models.bill import BillItemType

from .models import SponsorshipTypeBilling, bill_item_type_of


class BillItemTypeFormExtension:
    """Adds the bill item type to the sponsorship type form of huebhof_patenschaften."""

    def contribute(self, form):
        form.fields['bill_item_type'] = forms.ModelChoiceField(
            queryset=BillItemType.objects.all(), required=False, label=_('Rechnungspositionstyp'),
            initial=bill_item_type_of(form.instance) if form.instance.pk else None,
            help_text=_('Bestimmt das Buchungskonto auf der Rechnung. Leer: Rechnungspositionstyp "Patenschaft".'))

    def save(self, form, sponsorship_type):
        SponsorshipTypeBilling.objects.update_or_create(
            type=sponsorship_type, defaults={'bill_item_type': form.cleaned_data.get('bill_item_type')})
