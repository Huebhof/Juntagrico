from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ExportMixin

from juntagrico.entity.member import Member
from juntagrico.util import addons

from .models import Patenschaft, PatenschaftTyp


class PatenschaftResource(resources.ModelResource):
    vorname = fields.Field(attribute='member__first_name', column_name='Vorname')
    nachname = fields.Field(attribute='member__last_name', column_name='Nachname')
    email = fields.Field(attribute='member__email', column_name='E-Mail')
    typ_name = fields.Field(attribute='typ__name', column_name='Typ')
    status = fields.Field(column_name='Status')

    class Meta:
        model = Patenschaft
        fields = ('id', 'vorname', 'nachname', 'email', 'typ_name', 'jahresbeitrag',
                  'bestellt_am', 'aktiviert_am', 'gekuendigt_am', 'ende', 'status', 'notizen')
        export_order = fields

    def dehydrate_status(self, obj):
        return str(obj.get_status_display())


class StatusFilter(admin.SimpleListFilter):
    title = _('Status')
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [('bestellt', _('Bestellt')), ('aktiv', _('Aktiv')),
                ('gekuendigt', _('Gekündigt')), ('offen', _('Alle offenen'))]

    def queryset(self, request, queryset):
        if self.value() in ('bestellt', 'aktiv', 'gekuendigt', 'offen'):
            return getattr(queryset, self.value())()
        return queryset


@admin.register(PatenschaftTyp)
class PatenschaftTypAdmin(admin.ModelAdmin):
    list_display = ['name', 'jahresbeitrag', 'sichtbar', 'sortierung', 'anzahl_laufend']
    list_editable = ['sichtbar', 'sortierung']
    search_fields = ['name', 'beschreibung']

    @admin.display(description=_('Laufend'))
    def anzahl_laufend(self, obj):
        return obj.patenschaften.laufend().count()


@admin.register(Patenschaft)
class PatenschaftAdmin(ExportMixin, admin.ModelAdmin):
    resource_classes = [PatenschaftResource]
    list_display = ['member', 'typ', 'jahresbeitrag', 'bestellt_am', 'aktiviert_am', 'gekuendigt_am', 'ende',
                    'status_display']
    list_filter = [StatusFilter, 'typ', 'bestellt_am']
    search_fields = ['member__first_name', 'member__last_name', 'member__email', 'typ__name']
    autocomplete_fields = ['member']
    date_hierarchy = 'bestellt_am'
    actions = ['aktivieren', 'kuendigen']

    @admin.display(description=_('Status'))
    def status_display(self, obj):
        return obj.get_status_display()

    @admin.action(description=_('Ausgewählte Patenschaften aktivieren'))
    def aktivieren(self, request, queryset):
        anzahl = 0
        for p in queryset.bestellt():
            p.aktivieren()
            anzahl += 1
        self.message_user(request, _('{} Patenschaft(en) aktiviert.').format(anzahl), messages.SUCCESS)

    @admin.action(description=_('Ausgewählte Patenschaften kündigen (per Ende Geschäftsjahr)'))
    def kuendigen(self, request, queryset):
        anzahl = 0
        for p in queryset:
            if p.kann_gekuendigt_werden:
                p.kuendigen()
                anzahl += 1
        self.message_user(request, _('{} Patenschaft(en) gekündigt.').format(anzahl), messages.SUCCESS)


class PatenschaftInline(admin.TabularInline):
    model = Patenschaft
    fk_name = 'member'
    extra = 0
    fields = ['typ', 'jahresbeitrag', 'bestellt_am', 'aktiviert_am', 'gekuendigt_am', 'ende']
    show_change_link = True
    verbose_name_plural = _('Patenschaften')


# Patenschaften direkt beim Mitglied im Admin anzeigen.
# Funktioniert, weil diese App in INSTALLED_APPS vor juntagrico steht.
addons.config.register_model_inline(Member, PatenschaftInline)
