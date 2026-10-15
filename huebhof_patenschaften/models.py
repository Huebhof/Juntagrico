import datetime
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from juntagrico.entity.member import Member
from juntagrico.util import temporal


class PatenschaftTypQuerySet(models.QuerySet):
    def sichtbar(self):
        return self.filter(sichtbar=True)


class PatenschaftTyp(models.Model):
    """Eine Art von Patenschaft, z.B. "Baumpatenschaft" oder "Bienenpatenschaft"."""
    name = models.CharField(_('Name'), max_length=100)
    beschreibung = models.TextField(_('Beschreibung'), blank=True)
    jahresbeitrag = models.DecimalField(
        _('Jahresbeitrag'), max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))])
    sichtbar = models.BooleanField(
        _('Bestellbar'), default=True,
        help_text=_('Nur bestellbare Patenschaften werden bei der Anmeldung und im Mitgliederbereich angeboten.'))
    sortierung = models.PositiveIntegerField(_('Sortierung'), default=0)
    rechnungsposition = models.ForeignKey(
        'juntagrico_billing.BillItemType', verbose_name=_('Rechnungspositionstyp'),
        null=True, blank=True, on_delete=models.PROTECT, related_name='patenschaft_typen',
        help_text=_('Bestimmt das Buchungskonto auf der Rechnung. Leer: Rechnungspositionstyp "Patenschaft".'))

    objects = PatenschaftTypQuerySet.as_manager()

    class Meta:
        verbose_name = _('Patenschaftstyp')
        verbose_name_plural = _('Patenschaftstypen')
        ordering = ['sortierung', 'name']

    def __str__(self):
        return self.name


class PatenschaftQuerySet(models.QuerySet):
    def bestellt(self):
        """Bestellt, aber noch nicht aktiviert und nicht storniert."""
        return self.filter(aktiviert_am__isnull=True, gekuendigt_am__isnull=True)

    def laufend(self, date=None):
        """Aktiviert und noch nicht beendet (gekündigte bis zum Ende eingeschlossen)."""
        date = date or datetime.date.today()
        return self.filter(aktiviert_am__isnull=False, aktiviert_am__lte=date).filter(
            Q(ende__isnull=True) | Q(ende__gte=date))

    def aktiv(self, date=None):
        """Laufend und nicht gekündigt."""
        return self.laufend(date).filter(gekuendigt_am__isnull=True)

    def gekuendigt(self, date=None):
        """Gekündigt, läuft aber noch bis zum Ende."""
        return self.laufend(date).filter(gekuendigt_am__isnull=False)

    def offen(self, date=None):
        """Alles, was nicht beendet oder storniert ist."""
        date = date or datetime.date.today()
        return self.filter(Q(ende__isnull=True) | Q(ende__gte=date)).exclude(
            aktiviert_am__isnull=True, gekuendigt_am__isnull=False)


class Patenschaft(models.Model):
    """Eine von einem Mitglied übernommene Patenschaft. Mehrere gleiche = mehrere Datensätze."""
    member = models.ForeignKey(
        Member, verbose_name=_('Pat:in'), on_delete=models.PROTECT, related_name='patenschaften')
    typ = models.ForeignKey(
        PatenschaftTyp, verbose_name=_('Typ'), on_delete=models.PROTECT, related_name='patenschaften')
    jahresbeitrag = models.DecimalField(
        _('Jahresbeitrag'), max_digits=8, decimal_places=2,
        help_text=_('Beitrag zum Zeitpunkt der Bestellung. Spätere Preisänderungen am Typ wirken sich nicht aus.'))
    bestellt_am = models.DateField(_('Bestellt am'), default=datetime.date.today)
    aktiviert_am = models.DateField(_('Aktiviert am'), null=True, blank=True)
    gekuendigt_am = models.DateField(_('Gekündigt am'), null=True, blank=True)
    ende = models.DateField(_('Ende'), null=True, blank=True)
    notizen = models.TextField(_('Notizen'), blank=True)
    rechnungspositionen = models.ManyToManyField(
        'juntagrico_billing.BillItem', verbose_name=_('Rechnungspositionen'), blank=True,
        related_name='patenschaften')

    objects = PatenschaftQuerySet.as_manager()

    class Meta:
        verbose_name = _('Patenschaft')
        verbose_name_plural = _('Patenschaften')
        ordering = ['member__last_name', 'member__first_name', 'typ', 'bestellt_am']
        permissions = [
            ('notified_on_patenschaft_bestellung', _('Wird bei neuer Patenschaft per E-Mail informiert')),
            ('notified_on_patenschaft_kuendigung', _('Wird bei gekündigter Patenschaft per E-Mail informiert')),
        ]

    def __str__(self):
        return f'{self.typ} ({self.member})'

    def save(self, *args, **kwargs):
        if self.jahresbeitrag is None and self.typ_id:
            self.jahresbeitrag = self.typ.jahresbeitrag
        super().save(*args, **kwargs)

    @property
    def status(self):
        today = datetime.date.today()
        if self.aktiviert_am is None:
            return 'storniert' if self.gekuendigt_am else 'bestellt'
        if self.ende and self.ende < today:
            return 'beendet'
        if self.aktiviert_am > today:
            return 'bestellt'
        if self.gekuendigt_am:
            return 'gekuendigt'
        return 'aktiv'

    def get_status_display(self):
        return {
            'bestellt': _('Bestellt'),
            'aktiv': _('Aktiv'),
            'gekuendigt': _('Gekündigt'),
            'beendet': _('Beendet'),
            'storniert': _('Storniert'),
        }[self.status]

    @property
    def kann_gekuendigt_werden(self):
        return self.status in ('bestellt', 'aktiv')

    def aktivieren(self, date=None):
        if self.aktiviert_am is None:
            self.aktiviert_am = date or datetime.date.today()
            self.save()

    @staticmethod
    def naechstes_ende(date=None):
        """Ende bei Kündigung am angegebenen Datum: Ende des Geschäftsjahres, wenn die
        Kündigungsfrist (BUSINESS_YEAR_CANCELATION_MONTH) noch nicht vorbei ist,
        sonst Ende des folgenden Geschäftsjahres. Gleiche Regel wie bei den Ernteanteilen."""
        date = date or datetime.date.today()
        if date <= temporal.next_cancelation_date_from(temporal.start_of_specific_business_year(date)):
            return temporal.end_of_specific_business_year(date)
        return temporal.end_of_specific_business_year(temporal.end_of_specific_business_year(date)
                                                       + datetime.timedelta(days=1))

    def kuendigen(self, date=None):
        """Bestellte (noch nicht aktive) Patenschaften werden storniert,
        aktive laufen bis zum Ende des Geschäftsjahres."""
        date = date or datetime.date.today()
        if not self.kann_gekuendigt_werden:
            return
        self.gekuendigt_am = date
        if self.status == 'bestellt' or self.aktiviert_am is None:
            self.aktiviert_am = None
            self.ende = date
        else:
            self.ende = self.naechstes_ende(date)
        self.save()
