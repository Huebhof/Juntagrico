from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from juntagrico.util import addons

from huebhof_patenschaften.models import Sponsorship, SponsorshipType

from .models import SponsorshipBillItem, SponsorshipTypeBilling


class SponsorshipTypeBillingInline(admin.StackedInline):
    model = SponsorshipTypeBilling
    can_delete = False
    max_num = 1


class SponsorshipBillItemInline(admin.TabularInline):
    """Bills of a sponsorship (read only, they are created by the billing process)."""
    model = SponsorshipBillItem
    fields = ['bill']
    readonly_fields = ['bill']
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description=_('Rechnung'))
    def bill(self, obj):
        return format_html('<a href="{}">{}</a>',
                           reverse('admin:juntagrico_billing_bill_change', args=[obj.bill_item.bill_id]), obj)


# Works because this app comes before huebhof_patenschaften in INSTALLED_APPS.
addons.config.register_model_inline(SponsorshipType, SponsorshipTypeBillingInline)
addons.config.register_model_inline(Sponsorship, SponsorshipBillItemInline)
