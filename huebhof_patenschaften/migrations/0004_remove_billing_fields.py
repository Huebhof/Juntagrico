# The billing fields moved to the app huebhof_patenschaften_billing.
# Its migration 0001 copies the data first (run_before), if the app is installed.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('huebhof_patenschaften', '0003_english_names'),
    ]

    operations = [
        migrations.RemoveField(model_name='sponsorshiptype', name='bill_item_type'),
        migrations.RemoveField(model_name='sponsorship', name='bill_items'),
    ]
