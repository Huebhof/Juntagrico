# Replaces 0001-0005 (squashed by hand): the final state without the billing fields,
# so the app no longer depends on juntagrico_billing. Databases with 0001-0005 applied skip it.

import datetime
import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ('huebhof_patenschaften', '0001_initial'),
        ('huebhof_patenschaften', '0002_verrechnung'),
        ('huebhof_patenschaften', '0003_english_names'),
        ('huebhof_patenschaften', '0004_remove_billing_fields'),
        ('huebhof_patenschaften', '0005_max_count'),
    ]

    initial = True

    dependencies = [
        ('juntagrico', '0051_tour_weekday'),
    ]

    operations = [
        migrations.CreateModel(
            name='SponsorshipType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('description', models.TextField(blank=True, verbose_name='Beschreibung')),
                ('annual_fee', models.DecimalField(
                    decimal_places=2, max_digits=8,
                    validators=[django.core.validators.MinValueValidator(Decimal('0'))],
                    verbose_name='Jahresbeitrag')),
                ('visible', models.BooleanField(
                    default=True,
                    help_text='Nur bestellbare Patenschaften werden bei der Anmeldung und im Mitgliederbereich angeboten.',
                    verbose_name='Bestellbar')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Sortierung')),
                ('max_count', models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text='Leer: unbegrenzt. Gezählt werden laufende und bestellte, noch nicht aktivierte '
                              'Patenschaften. Ist die Anzahl erreicht, ist der Typ bei der Bestellung ausgebucht.',
                    verbose_name='Maximale Anzahl')),
            ],
            options={
                'verbose_name': 'Patenschaftstyp',
                'verbose_name_plural': 'Patenschaftstypen',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Sponsorship',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('annual_fee', models.DecimalField(
                    decimal_places=2, max_digits=8,
                    help_text='Beitrag zum Zeitpunkt der Bestellung. Spätere Preisänderungen am Typ wirken sich nicht aus.',
                    verbose_name='Jahresbeitrag')),
                ('order_date', models.DateField(default=datetime.date.today, verbose_name='Bestellt am')),
                ('activation_date', models.DateField(blank=True, null=True, verbose_name='Aktiviert am')),
                ('cancellation_date', models.DateField(blank=True, null=True, verbose_name='Gekündigt am')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='Ende')),
                ('notes', models.TextField(blank=True, verbose_name='Notizen')),
                ('member', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name='sponsorships',
                    to='juntagrico.member', verbose_name='Pat:in')),
                ('type', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name='sponsorships',
                    to='huebhof_patenschaften.sponsorshiptype', verbose_name='Typ')),
            ],
            options={
                'verbose_name': 'Patenschaft',
                'verbose_name_plural': 'Patenschaften',
                'ordering': ['member__last_name', 'member__first_name', 'type', 'order_date'],
                'permissions': [
                    ('notified_on_sponsorship_creation', 'Wird bei neuer Patenschaft per E-Mail informiert'),
                    ('notified_on_sponsorship_cancellation', 'Wird bei gekündigter Patenschaft per E-Mail informiert'),
                ],
            },
        ),
    ]
