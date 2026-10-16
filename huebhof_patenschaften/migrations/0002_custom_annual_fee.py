from decimal import Decimal

import django.core.validators
from django.db import migrations, models
from django.db.models import F


def clear_type_fees(apps, schema_editor):
    """Sponsorships with the fee of their type follow the type from now on, the others keep their fee."""
    Sponsorship = apps.get_model('huebhof_patenschaften', 'Sponsorship')
    Sponsorship.objects.filter(custom_annual_fee=F('type__annual_fee')).update(custom_annual_fee=None)


def fill_type_fees(apps, schema_editor):
    Sponsorship = apps.get_model('huebhof_patenschaften', 'Sponsorship')
    for s in Sponsorship.objects.filter(custom_annual_fee__isnull=True).select_related('type'):
        s.custom_annual_fee = s.type.annual_fee
        s.save(update_fields=['custom_annual_fee'])


class Migration(migrations.Migration):

    dependencies = [
        ('huebhof_patenschaften', '0001_squashed_0005_max_count'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sponsorship',
            old_name='annual_fee',
            new_name='custom_annual_fee',
        ),
        migrations.AlterField(
            model_name='sponsorship',
            name='custom_annual_fee',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0'))],
                verbose_name='Abweichender Jahresbeitrag',
                help_text='Leer: Jahresbeitrag des Typs, Preisänderungen am Typ gelten auch für diese Patenschaft. '
                          'Nur für Ausnahmen ausfüllen, z.B. einen Sonderpreis; dieser bleibt fix.'),
        ),
        migrations.RunPython(clear_type_fees, fill_type_fees),
    ]
