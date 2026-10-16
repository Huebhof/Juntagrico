import datetime
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from juntagrico.entity.member import Member
from juntagrico.util import temporal


class SponsorshipTypeQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(visible=True)


class SponsorshipType(models.Model):
    """A kind of sponsorship, e.g. "tree sponsorship" or "bee sponsorship"."""
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Beschreibung'), blank=True)
    annual_fee = models.DecimalField(
        _('Jahresbeitrag'), max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))])
    visible = models.BooleanField(
        _('Bestellbar'), default=True,
        help_text=_('Nur bestellbare Patenschaften werden bei der Anmeldung und im Mitgliederbereich angeboten.'))
    sort_order = models.PositiveIntegerField(_('Sortierung'), default=0)
    bill_item_type = models.ForeignKey(
        'juntagrico_billing.BillItemType', verbose_name=_('Rechnungspositionstyp'),
        null=True, blank=True, on_delete=models.PROTECT, related_name='sponsorship_types',
        help_text=_('Bestimmt das Buchungskonto auf der Rechnung. Leer: Rechnungspositionstyp "Patenschaft".'))

    objects = SponsorshipTypeQuerySet.as_manager()

    class Meta:
        verbose_name = _('Patenschaftstyp')
        verbose_name_plural = _('Patenschaftstypen')
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class SponsorshipQuerySet(models.QuerySet):
    def ordered(self):
        """Ordered, but neither activated nor withdrawn."""
        return self.filter(activation_date__isnull=True, cancellation_date__isnull=True)

    def running(self, date=None):
        """Activated and not yet ended (canceled ones included until their end date)."""
        date = date or datetime.date.today()
        return self.filter(activation_date__isnull=False, activation_date__lte=date).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=date))

    def active(self, date=None):
        """Running and not canceled."""
        return self.running(date).filter(cancellation_date__isnull=True)

    def canceled(self, date=None):
        """Canceled, but still running until the end date."""
        return self.running(date).filter(cancellation_date__isnull=False)

    def open(self, date=None):
        """Everything that is neither ended nor withdrawn."""
        date = date or datetime.date.today()
        return self.filter(Q(end_date__isnull=True) | Q(end_date__gte=date)).exclude(
            activation_date__isnull=True, cancellation_date__isnull=False)


class Sponsorship(models.Model):
    """A sponsorship taken over by a member. Several of the same type = several records."""
    ORDERED = 'ordered'
    ACTIVE = 'active'
    CANCELED = 'canceled'
    ENDED = 'ended'
    WITHDRAWN = 'withdrawn'

    member = models.ForeignKey(
        Member, verbose_name=_('Pat:in'), on_delete=models.PROTECT, related_name='sponsorships')
    type = models.ForeignKey(
        SponsorshipType, verbose_name=_('Typ'), on_delete=models.PROTECT, related_name='sponsorships')
    annual_fee = models.DecimalField(
        _('Jahresbeitrag'), max_digits=8, decimal_places=2,
        help_text=_('Beitrag zum Zeitpunkt der Bestellung. Spätere Preisänderungen am Typ wirken sich nicht aus.'))
    order_date = models.DateField(_('Bestellt am'), default=datetime.date.today)
    activation_date = models.DateField(_('Aktiviert am'), null=True, blank=True)
    cancellation_date = models.DateField(_('Gekündigt am'), null=True, blank=True)
    end_date = models.DateField(_('Ende'), null=True, blank=True)
    notes = models.TextField(_('Notizen'), blank=True)
    bill_items = models.ManyToManyField(
        'juntagrico_billing.BillItem', verbose_name=_('Rechnungspositionen'), blank=True,
        related_name='sponsorships')

    objects = SponsorshipQuerySet.as_manager()

    class Meta:
        verbose_name = _('Patenschaft')
        verbose_name_plural = _('Patenschaften')
        ordering = ['member__last_name', 'member__first_name', 'type', 'order_date']
        permissions = [
            ('notified_on_sponsorship_creation', _('Wird bei neuer Patenschaft per E-Mail informiert')),
            ('notified_on_sponsorship_cancellation', _('Wird bei gekündigter Patenschaft per E-Mail informiert')),
        ]

    def __str__(self):
        return f'{self.type} ({self.member})'

    def save(self, *args, **kwargs):
        if self.annual_fee is None and self.type_id:
            self.annual_fee = self.type.annual_fee
        super().save(*args, **kwargs)

    @property
    def status(self):
        today = datetime.date.today()
        if self.activation_date is None:
            return self.WITHDRAWN if self.cancellation_date else self.ORDERED
        if self.end_date and self.end_date < today:
            return self.ENDED
        if self.activation_date > today:
            return self.ORDERED
        if self.cancellation_date:
            return self.CANCELED
        return self.ACTIVE

    def get_status_display(self):
        return {
            self.ORDERED: _('Bestellt'),
            self.ACTIVE: _('Aktiv'),
            self.CANCELED: _('Gekündigt'),
            self.ENDED: _('Beendet'),
            self.WITHDRAWN: _('Storniert'),
        }[self.status]

    @property
    def can_be_canceled(self):
        return self.status in (self.ORDERED, self.ACTIVE)

    def activate(self, date=None):
        if self.activation_date is None:
            self.activation_date = date or datetime.date.today()
            self.save()

    @staticmethod
    def next_end_date(date=None):
        """End date when canceling on the given date: end of the business year if the cancellation
        period (BUSINESS_YEAR_CANCELATION_MONTH) has not passed yet, otherwise end of the following
        business year. Same rule as for subscriptions."""
        date = date or datetime.date.today()
        if date <= temporal.next_cancelation_date_from(temporal.start_of_specific_business_year(date)):
            return temporal.end_of_specific_business_year(date)
        return temporal.end_of_specific_business_year(temporal.end_of_specific_business_year(date)
                                                       + datetime.timedelta(days=1))

    def cancel(self, date=None):
        """Ordered (not yet active) sponsorships are withdrawn,
        active ones run until the end of the business year."""
        date = date or datetime.date.today()
        if not self.can_be_canceled:
            return
        self.cancellation_date = date
        if self.status == self.ORDERED or self.activation_date is None:
            self.activation_date = None
            self.end_date = date
        else:
            self.end_date = self.next_end_date(date)
        self.save()
