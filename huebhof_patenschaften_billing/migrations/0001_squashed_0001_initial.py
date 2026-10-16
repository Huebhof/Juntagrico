# Replaces 0001_initial (squashed by hand) without the data copy from the former billing fields
# of huebhof_patenschaften, which no longer exist in its squashed migration.
# Databases with 0001_initial applied skip it.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ('huebhof_patenschaften_billing', '0001_initial'),
    ]

    initial = True

    dependencies = [
        ('huebhof_patenschaften', '0001_squashed_0005_max_count'),
        ('juntagrico_billing', '0006_alter_payment_paid_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='SponsorshipTypeBilling',
            fields=[
                ('type', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='billing',
                    serialize=False, to='huebhof_patenschaften.sponsorshiptype', verbose_name='Patenschaftstyp')),
                ('bill_item_type', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name='sponsorship_types', to='juntagrico_billing.billitemtype',
                    verbose_name='Rechnungspositionstyp',
                    help_text='Bestimmt das Buchungskonto auf der Rechnung. Leer: Rechnungspositionstyp "Patenschaft".')),
            ],
            options={'verbose_name': 'Verrechnung', 'verbose_name_plural': 'Verrechnung'},
        ),
        migrations.CreateModel(
            name='SponsorshipBillItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sponsorship', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='bill_item_links',
                    to='huebhof_patenschaften.sponsorship', verbose_name='Patenschaft')),
                ('bill_item', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, related_name='sponsorship_link',
                    to='juntagrico_billing.billitem', verbose_name='Rechnungsposition')),
            ],
            options={'verbose_name': 'Rechnung', 'verbose_name_plural': 'Rechnungen',
                     'ordering': ['bill_item__bill__business_year__start_date']},
        ),
    ]
