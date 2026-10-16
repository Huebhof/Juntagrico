from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from adminsortable2.admin import SortableAdminMixin
from import_export.admin import ExportMixin

from juntagrico.admins import BaseAdmin
from juntagrico.entity.member import Member
from juntagrico.util import addons

from . import services
from .models import Sponsorship, SponsorshipType


class SponsorshipResource(resources.ModelResource):
    first_name = fields.Field(attribute='member__first_name', column_name='Vorname')
    last_name = fields.Field(attribute='member__last_name', column_name='Nachname')
    email = fields.Field(attribute='member__email', column_name='E-Mail')
    type_name = fields.Field(attribute='type__name', column_name='Typ')
    annual_fee = fields.Field(attribute='annual_fee', column_name='Jahresbeitrag')
    custom_annual_fee = fields.Field(attribute='custom_annual_fee', column_name='Sonderpreis')
    order_date = fields.Field(attribute='order_date', column_name='Bestellt am')
    activation_date = fields.Field(attribute='activation_date', column_name='Aktiviert am')
    cancellation_date = fields.Field(attribute='cancellation_date', column_name='Gekündigt am')
    end_date = fields.Field(attribute='end_date', column_name='Ende')
    status = fields.Field(column_name='Status')
    notes = fields.Field(attribute='notes', column_name='Notizen')

    class Meta:
        model = Sponsorship
        fields = ('id', 'first_name', 'last_name', 'email', 'type_name', 'annual_fee', 'custom_annual_fee',
                  'order_date', 'activation_date', 'cancellation_date', 'end_date', 'status', 'notes')
        export_order = fields

    def dehydrate_status(self, obj):
        return str(obj.get_status_display())


class StatusFilter(admin.SimpleListFilter):
    title = _('Status')
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [('ordered', _('Bestellt')), ('active', _('Aktiv')),
                ('canceled', _('Gekündigt')), ('open', _('Alle offenen'))]

    def queryset(self, request, queryset):
        if self.value() in ('ordered', 'active', 'canceled', 'open'):
            return getattr(queryset, self.value())()
        return queryset


@admin.register(SponsorshipType)
class SponsorshipTypeAdmin(SortableAdminMixin, BaseAdmin):
    list_display = ['name', 'annual_fee', 'visible', 'max_count', 'running_count']
    list_editable = ['visible']
    search_fields = ['name', 'description']

    @admin.display(description=_('Laufend'))
    def running_count(self, obj):
        return obj.sponsorships.running().count()


@admin.register(Sponsorship)
class SponsorshipAdmin(ExportMixin, BaseAdmin):
    resource_classes = [SponsorshipResource]
    list_display = ['member', 'type', 'annual_fee', 'order_date', 'activation_date', 'cancellation_date', 'end_date',
                    'status_display']
    list_filter = [StatusFilter, 'type', 'order_date']
    search_fields = ['member__first_name', 'member__last_name', 'member__email', 'type__name']
    autocomplete_fields = ['member']
    date_hierarchy = 'order_date'
    actions = ['activate', 'cancel']

    @admin.display(description=_('Status'))
    def status_display(self, obj):
        return obj.get_status_display()

    @admin.action(description=_('Ausgewählte Patenschaften aktivieren (mit Bestätigungsmail)'))
    def activate(self, request, queryset):
        count = len(services.activate(queryset.ordered()))
        self.message_user(request, _('{} Patenschaft(en) aktiviert.').format(count), messages.SUCCESS)

    @admin.action(description=_('Ausgewählte Patenschaften kündigen (per Ende Geschäftsjahr)'))
    def cancel(self, request, queryset):
        count = 0
        for s in queryset:
            if s.can_be_canceled:
                s.cancel()
                count += 1
        self.message_user(request, _('{} Patenschaft(en) gekündigt.').format(count), messages.SUCCESS)


class SponsorshipInline(admin.TabularInline):
    model = Sponsorship
    fk_name = 'member'
    extra = 0
    fields = ['type', 'custom_annual_fee', 'order_date', 'activation_date', 'cancellation_date', 'end_date']
    show_change_link = True
    verbose_name_plural = _('Patenschaften')


# Show sponsorships directly on the member in the admin.
# Works because this app comes before juntagrico in INSTALLED_APPS.
addons.config.register_model_inline(Member, SponsorshipInline)
