# Takes over the billing fields that were part of huebhof_patenschaften until migration 0003.
# Runs before huebhof_patenschaften 0004, which removes them there.

import django.db.models.deletion
from django.db import migrations, models


def copy_from_sponsorships(apps, schema_editor):
    SponsorshipType = apps.get_model('huebhof_patenschaften', 'SponsorshipType')
    Sponsorship = apps.get_model('huebhof_patenschaften', 'Sponsorship')
    SponsorshipTypeBilling = apps.get_model('huebhof_patenschaften_billing', 'SponsorshipTypeBilling')
    SponsorshipBillItem = apps.get_model('huebhof_patenschaften_billing', 'SponsorshipBillItem')
    for sponsorship_type in SponsorshipType.objects.exclude(bill_item_type=None):
        SponsorshipTypeBilling.objects.create(type_id=sponsorship_type.id,
                                              bill_item_type_id=sponsorship_type.bill_item_type_id)
    for link in Sponsorship.bill_items.through.objects.all():
        SponsorshipBillItem.objects.create(sponsorship_id=link.sponsorship_id, bill_item_id=link.billitem_id)


def copy_to_sponsorships(apps, schema_editor):
    SponsorshipType = apps.get_model('huebhof_patenschaften', 'SponsorshipType')
    Sponsorship = apps.get_model('huebhof_patenschaften', 'Sponsorship')
    SponsorshipTypeBilling = apps.get_model('huebhof_patenschaften_billing', 'SponsorshipTypeBilling')
    SponsorshipBillItem = apps.get_model('huebhof_patenschaften_billing', 'SponsorshipBillItem')
    for billing in SponsorshipTypeBilling.objects.exclude(bill_item_type=None):
        SponsorshipType.objects.filter(id=billing.type_id).update(bill_item_type_id=billing.bill_item_type_id)
    Through = Sponsorship.bill_items.through
    for link in SponsorshipBillItem.objects.all():
        Through.objects.create(sponsorship_id=link.sponsorship_id, billitem_id=link.bill_item_id)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('huebhof_patenschaften', '0003_english_names'),
        ('juntagrico_billing', '0006_alter_payment_paid_date'),
    ]

    run_before = [
        ('huebhof_patenschaften', '0004_remove_billing_fields'),
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
        migrations.RunPython(copy_from_sponsorships, copy_to_sponsorships),
    ]
